"""Public API v1: Tra cứu số dư Credit & Hạn mức Rate limit."""
import logging
from typing import Tuple

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limiter import RATE_LIMITS_BY_PLAN
from app.db import get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.routes.v1.dependencies import get_v1_api_user
from app.schemas.api_key import V1CreditsResponse
from app.services.api_key_service import ApiKeyService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/credits",
    response_model=V1CreditsResponse,
    summary="Kiểm tra số dư Credit và hạn mức gọi API theo gói cước",
)
async def get_v1_credits(
    request: Request,
    auth_data: Tuple[ApiKey, User] = Depends(get_v1_api_user),
    db: AsyncSession = Depends(get_db),
) -> V1CreditsResponse:
    """
    Trả về thông tin tài khoản sở hữu API Key:
    - Số dư credit khả dụng
    - Hạng gói cước (free, pro, vip, admin)
    - Giới hạn tần suất gọi API (requests/phút)
    """
    api_key, user = auth_data

    raw_tier = getattr(user, "subscription_tier", "free") or "free"
    plan_tier = "admin" if user.is_admin else raw_tier.lower()
    rate_limit = RATE_LIMITS_BY_PLAN.get(plan_tier, 20)

    # Ghi log API usage
    client_ip = request.client.host if request.client else None
    await ApiKeyService.log_usage(
        db=db,
        api_key_id=api_key.id,
        user_id=user.id,
        endpoint="/v1/credits",
        status_code=200,
        credits_used=0,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
    )

    return V1CreditsResponse(
        credit_balance=user.credit_balance,
        plan_tier=plan_tier,
        rate_limit_per_minute=rate_limit,
        user_email=user.email,
    )
