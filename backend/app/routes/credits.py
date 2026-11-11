"""Routes quản lý Credit và lịch sử giao dịch sổ cái."""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.services.credit_service import CreditService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/credits", tags=["Credits"])


class CreditBalanceResponse(BaseModel):
    user_id: int
    balance: int
    chars_per_credit: int
    provider_multipliers: dict[str, float]


class CreditTransactionItem(BaseModel):
    id: int
    user_id: int
    amount: int
    type: str
    ref_id: Optional[str] = None
    balance_after: int
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreditTransactionsListResponse(PaginatedResponse[CreditTransactionItem]):
    """Danh sách giao dịch credit có phân trang."""
    pass


class CreditEstimateResponse(BaseModel):
    char_count: int
    provider: str
    voice: Optional[str] = None
    multiplier: float
    estimated_credits: int


@router.get("", response_model=CreditBalanceResponse, summary="Lấy số dư credit hiện tại")
async def get_credit_balance(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Trả về số dư credit của tài khoản người dùng đăng nhập."""
    settings = get_settings()
    balance = await CreditService.get_balance(db, current_user.id)
    return CreditBalanceResponse(
        user_id=current_user.id,
        balance=balance,
        chars_per_credit=settings.credit_chars_per_credit,
        provider_multipliers=settings.credit_provider_multipliers,
    )


@router.get(
    "/transactions",
    response_model=CreditTransactionsListResponse,
    summary="Lịch sử giao dịch biến động credit (Sổ cái)",
)
async def get_credit_transactions(
    page: int = Query(1, ge=1, description="Số trang (bắt đầu từ 1)"),
    limit: int = Query(20, ge=1, le=100, description="Số bản ghi mỗi trang"),
    type: Optional[str] = Query(None, description="Lọc theo loại giao dịch (signup_bonus, usage, refund...)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trả về danh sách lịch sử biến động credit dạng sổ cái có phân trang và lọc theo loại giao dịch.
    """
    items, total = await CreditService.list_transactions(
        db=db,
        user_id=current_user.id,
        page=page,
        limit=limit,
        tx_type=type,
    )
    total_pages = max(1, (total + limit - 1) // limit) if total > 0 else 1

    return CreditTransactionsListResponse(
        items=[CreditTransactionItem.model_validate(tx) for tx in items],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/estimate", response_model=CreditEstimateResponse, summary="Ước tính số credit cần dùng")
async def estimate_credits(
    chars: int = Query(..., ge=0, description="Số lượng ký tự văn bản"),
    provider: str = Query("edge", description="Nhà cung cấp TTS (edge, azure, elevenlabs)"),
    voice: Optional[str] = Query(None, description="Giọng đọc"),
):
    """Tính toán trước số credit sẽ tiêu tốn cho độ dài văn bản và provider tương ứng."""
    settings = get_settings()
    provider_clean = provider.lower().strip()
    multiplier = settings.credit_provider_multipliers.get(provider_clean, 1.0)
    estimated = CreditService.calculate_cost(chars, provider=provider_clean, voice=voice or "")

    return CreditEstimateResponse(
        char_count=chars,
        provider=provider_clean,
        voice=voice,
        multiplier=multiplier,
        estimated_credits=estimated,
    )
