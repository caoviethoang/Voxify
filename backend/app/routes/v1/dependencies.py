"""Dependencies xác thực & kiểm soát tần suất (Rate Limiter) cho Public API v1."""
import logging
from typing import Tuple

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limiter import RateLimiterService
from app.core.security import get_client_ip
from app.db import get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.services.api_key_service import ApiKeyService

logger = logging.getLogger(__name__)


async def get_v1_api_user(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> Tuple[ApiKey, User]:
    """
    Xác thực API Key qua header Authorization: Bearer <api_key>:
    - Kiểm tra định dạng token (bắt đầu bằng vx_live_).
    - So khớp hash SHA-256 trong cơ sở dữ liệu.
    - Kiểm tra trạng thái is_active (trả về 401 nếu revoked hoặc không tồn tại).
    - Áp dụng Rate Limiting theo cấp độ tài khoản (free: 20, pro: 60, vip: 120, admin: 300 req/min).
    - Thêm các headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset.
    - Trả HTTP 429 kèm Retry-After nếu vượt quá giới hạn.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thiếu hoặc sai định dạng header Authorization. Vui lòng truyền: Authorization: Bearer vx_live_...",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raw_key = auth_header[7:].strip()
    auth_result = await ApiKeyService.verify_api_key(db, raw_key)
    if not auth_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key không hợp lệ, không tồn tại hoặc đã bị thu hồi.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    api_key, user = auth_result

    # Xác định gói cước rate limit
    raw_tier = getattr(user, "subscription_tier", "free") or "free"
    plan_tier = "admin" if user.is_admin else raw_tier.lower()
    allowed, limit, remaining, reset_seconds = await RateLimiterService.check_rate_limit(
        api_key_id=api_key.id,
        plan_name=plan_tier,
    )

    # Đính kèm rate limit headers chuẩn RFC
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_seconds)

    if not allowed:
        response.headers["Retry-After"] = str(reset_seconds)
        # Ghi nhận log request bị chặn rate limit
        client_ip = get_client_ip(request)
        await ApiKeyService.log_usage(
            db=db,
            api_key_id=api_key.id,
            user_id=user.id,
            endpoint=request.url.path,
            status_code=429,
            credits_used=0,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Đã vượt quá giới hạn tần suất gọi API ({limit} req/phút cho gói {plan_tier.upper()}). Vui lòng thử lại sau {reset_seconds} giây.",
            headers={"Retry-After": str(reset_seconds)},
        )

    return api_key, user
