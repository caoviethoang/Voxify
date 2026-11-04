"""Bộ giới hạn tốc độ yêu cầu (Rate Limiter) chống brute force."""
import time
from collections import defaultdict
from threading import Lock
from fastapi import HTTPException, Request

# Lưu timestamps các lần thử: { ip: [timestamp1, timestamp2, ...] }
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
    # Kiểm tra header X-Forwarded-For nếu chạy sau reverse proxy
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    now = time.time()
    cutoff = now - window_seconds

    with _lock:
        # Lọc bỏ các timestamp ngoài khoảng thời gian window
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
