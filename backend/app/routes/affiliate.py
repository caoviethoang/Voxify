"""Routes API cho Chương trình Tiếp thị liên kết (Affiliate Program - Issue #14)."""
import logging
from typing import List

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import get_client_ip
from app.db import get_db
from app.dependencies import get_current_active_user
from app.models.admin import AffiliateWithdrawal
from app.models.affiliate import AffiliateCommission
from app.models.payment import Order
from app.models.user import User
from app.schemas.affiliate import (
    AffiliateCommissionItem,
    AffiliateCustomizeCodeRequest,
    AffiliateCustomizeCodeResponse,
    AffiliateDashboardResponse,
    AffiliateTrackResponse,
    AffiliateWithdrawalItem,
    AffiliateWithdrawalRequest,
)
from app.services.affiliate_service import AffiliateService, mask_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/affiliate", tags=["Affiliate Program"])


@router.post("/track", response_model=AffiliateTrackResponse, summary="Ghi nhận lượt click link Affiliate & lưu Cookie 30 ngày")
async def track_affiliate_click(
    request: Request,
    response: Response,
    ref: str = Query(..., min_length=2, max_length=50, description="Mã giới thiệu Affiliate"),
    db: AsyncSession = Depends(get_db),
):
    """
    Theo dõi lượt click vào đường link giới thiệu.
    Lưu cookie theo dõi 30 ngày trên trình duyệt khách truy cập (Req #1).
    """
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent")
    device_fingerprint = request.headers.get("x-device-fingerprint")

    success, message, _ = await AffiliateService.record_click(
        db=db,
        referral_code=ref,
        ip_address=client_ip,
        user_agent=user_agent,
        device_fingerprint=device_fingerprint,
    )

    if success:
        settings = get_settings()
        cookie_days = getattr(settings, "affiliate_cookie_days", 30)
        max_age = cookie_days * 86400
        response.set_cookie(
            key="voxify_ref",
            value=ref.strip().upper(),
            max_age=max_age,
            expires=max_age,
            httponly=False,  # Để frontend có thể đọc và đồng bộ UI
            samesite="lax",
            secure=not settings.debug,
            path="/",
        )

    return AffiliateTrackResponse(
        success=success,
        referral_code=ref.strip().upper(),
        message=message,
    )


@router.get("/dashboard", response_model=AffiliateDashboardResponse, summary="Lấy thống kê tổng quan và lịch sử Dashboard Affiliate")
async def get_affiliate_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Thống kê chi tiết link giới thiệu, số click, đăng ký, đơn hàng, hoa hồng và rút tiền (Req #3)."""
    data = await AffiliateService.get_affiliate_stats(db, current_user)
    return AffiliateDashboardResponse(**data)


@router.post("/withdraw", response_model=AffiliateWithdrawalItem, status_code=status.HTTP_201_CREATED, summary="Gửi yêu cầu rút tiền hoa hồng")
async def request_affiliate_withdrawal(
    body: AffiliateWithdrawalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Gửi yêu cầu rút tiền hoa hồng về tài khoản ngân hàng (Req #4)."""
    withdrawal = await AffiliateService.request_payout(
        db=db,
        user=current_user,
        amount=body.amount,
        bank_name=body.bank_name,
        bank_account_number=body.bank_account_number,
        bank_account_holder=body.bank_account_holder,
    )
    return AffiliateWithdrawalItem.model_validate(withdrawal)


@router.put("/code", response_model=AffiliateCustomizeCodeResponse, summary="Tùy chỉnh mã giới thiệu cá nhân")
async def customize_referral_code(
    body: AffiliateCustomizeCodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Thay đổi mã giới thiệu cá nhân theo sở thích."""
    new_code = await AffiliateService.customize_code(
        db=db,
        user=current_user,
        new_code=body.referral_code,
    )
    settings = get_settings()
    frontend_url = settings.frontend_url.rstrip("/")
    return AffiliateCustomizeCodeResponse(
        success=True,
        referral_code=new_code,
        referral_link=f"{frontend_url}/register?ref={new_code}",
        message="Cập nhật mã giới thiệu thành công",
    )


@router.get("/commissions", response_model=List[AffiliateCommissionItem], summary="Danh sách lịch sử hoa hồng")
async def list_commissions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Xem danh sách chi tiết các khoản hoa hồng của người dùng."""
    await AffiliateService.settle_pending_commissions(db)

    offset = (page - 1) * limit
    stmt = (
        select(AffiliateCommission, Order.order_code, User.email.label("buyer_email"))
        .join(Order, AffiliateCommission.order_id == Order.id)
        .join(User, AffiliateCommission.referred_user_id == User.id)
        .where(AffiliateCommission.affiliate_user_id == current_user.id)
        .order_by(desc(AffiliateCommission.created_at))
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    results = []
    for comm, order_code, buyer_email in rows:
        results.append(
            AffiliateCommissionItem(
                id=comm.id,
                order_code=order_code,
                buyer_masked_email=mask_email(buyer_email),
                order_amount=comm.order_amount,
                commission_rate=comm.commission_rate,
                amount=comm.amount,
                status=comm.status,
                hold_until=comm.hold_until,
                created_at=comm.created_at,
            )
        )
    return results


@router.get("/withdrawals", response_model=List[AffiliateWithdrawalItem], summary="Danh sách lịch sử rút tiền")
async def list_withdrawals(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Xem danh sách các yêu cầu rút tiền của người dùng."""
    offset = (page - 1) * limit
    stmt = (
        select(AffiliateWithdrawal)
        .where(AffiliateWithdrawal.user_id == current_user.id)
        .order_by(desc(AffiliateWithdrawal.created_at))
        .offset(offset)
        .limit(limit)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return [AffiliateWithdrawalItem.model_validate(it) for it in items]
