"""Bộ giới hạn tốc độ yêu cầu (Rate Limiter) chống brute force & điều tiết Public API (Issue #13)."""
import logging
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List, Tuple

from fastapi import HTTPException, Request

from app.config import get_settings

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# 1. Rate Limiting cho Đăng nhập (Brute-force protection)
# ----------------------------------------------------------------------
_attempts: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def check_login_rate_limit(
    request: Request,
    max_attempts: int = 5,
    window_seconds: int = 60,
) -> None:
    """
    Kiểm tra giới hạn số lần đăng nhập (5 lần / phút / IP).
    Nếu vượt quá, trả lỗi HTTP 429 Too Many Requests.
    """
    client_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    now = time.time()
    cutoff = now - window_seconds

    with _lock:
        recent = [t for t in _attempts[client_ip] if t > cutoff]
        if len(recent) >= max_attempts:
            retry_after = int(window_seconds - (now - recent[0])) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Quá nhiều lần đăng nhập không thành công. Vui lòng thử lại sau {retry_after} giây.",
                headers={"Retry-After": str(retry_after)},
            )
        recent.append(now)
        _attempts[client_ip] = recent


def reset_login_rate_limit(request: Request) -> None:
    """Xóa lịch sử lần thử của IP sau khi đăng nhập thành công."""
    client_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    with _lock:
        if client_ip in _attempts:
            _attempts.pop(client_ip, None)


# ----------------------------------------------------------------------
# 2. Rate Limiting cho Public API v1 theo API Key & Plan Tier
# ----------------------------------------------------------------------
RATE_LIMITS_BY_PLAN: Dict[str, int] = {
    "free": 20,
    "pro": 60,
    "vip": 120,
    "admin": 300,
}
DEFAULT_RATE_LIMIT = 20
WINDOW_SECONDS = 60


class MemorySlidingWindowRateLimiter:
    """
    Sliding window counter lưu trong bộ nhớ:
    - Lưu danh sách timestamp của các request gần nhất trong 60 giây.
    - Dùng làm dự phòng (fallback) an toàn khi Redis không sẵn sàng hoặc chạy offline.
    """

    def __init__(self) -> None:
        self._requests: Dict[str, List[float]] = {}

    def is_allowed(self, key_id: str, limit: int) -> Tuple[bool, int, int]:
        """
        Kiểm tra request có được phép hay không.
        Trả về tuple: (allowed: bool, remaining: int, reset_seconds: int)
        """
        now = time.time()
        window_start = now - WINDOW_SECONDS

        timestamps = self._requests.setdefault(key_id, [])
        self._requests[key_id] = [ts for ts in timestamps if ts > window_start]
        timestamps = self._requests[key_id]

        current_count = len(timestamps)
        if current_count >= limit:
            oldest_ts = timestamps[0]
            reset_seconds = max(1, int(WINDOW_SECONDS - (now - oldest_ts)))
            return False, 0, reset_seconds

        timestamps.append(now)
        remaining = max(0, limit - len(timestamps))
        oldest_ts = timestamps[0]
        reset_seconds = max(1, int(WINDOW_SECONDS - (now - oldest_ts)))
        return True, remaining, reset_seconds

    def reset(self) -> None:
        """Xóa toàn bộ cache rate limit (phục vụ unit test)."""
        self._requests.clear()


_memory_limiter = MemorySlidingWindowRateLimiter()


class RateLimiterService:
    """
    Dịch vụ kiểm tra Rate Limit:
    Ưu tiên Redis nếu có kết nối, tự động fallback MemorySlidingWindow.
    """

    @classmethod
    async def check_rate_limit(
        cls,
        api_key_id: int,
        plan_name: str = "free",
    ) -> Tuple[bool, int, int, int]:
        """
        Kiểm tra rate limit cho API key.
        Trả về tuple: (allowed, limit, remaining, reset_seconds)
        """
        limit = RATE_LIMITS_BY_PLAN.get(plan_name.lower(), DEFAULT_RATE_LIMIT)
        cache_key = f"rl:api_key:{api_key_id}"

        settings = get_settings()
        redis_url = getattr(settings, "redis_url", "")

        if redis_url and not getattr(settings, "environment", "").lower() == "testing":
            try:
                import redis.asyncio as aioredis

                r = aioredis.from_url(redis_url, decode_responses=True, socket_timeout=1.0)
                pipe = r.pipeline()
                now = time.time()
                window_start = now - WINDOW_SECONDS

                pipe.zremrangebyscore(cache_key, 0, window_start)
                pipe.zcard(cache_key)
                pipe.zrange(cache_key, 0, 0, withscores=True)
                results = await pipe.execute()
                await r.aclose()

                current_count = int(results[1])
                oldest_entries = results[2]

                if oldest_entries:
                    oldest_ts = float(oldest_entries[0][1])
                    reset_seconds = max(1, int(WINDOW_SECONDS - (now - oldest_ts)))
                else:
                    reset_seconds = WINDOW_SECONDS

                if current_count >= limit:
                    return False, limit, 0, reset_seconds

                r2 = aioredis.from_url(redis_url, decode_responses=True, socket_timeout=1.0)
                p2 = r2.pipeline()
                p2.zadd(cache_key, {str(now): now})
                p2.expire(cache_key, WINDOW_SECONDS + 5)
                await p2.execute()
                await r2.aclose()

                remaining = max(0, limit - (current_count + 1))
                return True, limit, remaining, reset_seconds
            except Exception as e:
                logger.debug(f"Redis rate limit không khả dụng ({e}), chuyển sang memory limiter.")

        allowed, remaining, reset_seconds = _memory_limiter.is_allowed(str(api_key_id), limit)
        return allowed, limit, remaining, reset_seconds

    @classmethod
    def reset_in_memory(cls) -> None:
        """Reset bộ đếm in-memory (dùng cho unit test)."""
        _memory_limiter.reset()
