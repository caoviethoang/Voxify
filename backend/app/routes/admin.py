"""Router API dành riêng cho Quản trị viên (Admin Portal - Issue #15)."""
import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_client_ip
from app.db import get_db
from app.dependencies import get_current_admin_user, get_tts_service
from app.models.admin import (
    AffiliateWithdrawal,
    SystemSetting,
    SystemVoiceSetting,
)
from app.models.credit import CreditTransaction, CreditTransactionType
from app.models.generation import Generation
from app.models.payment import Coupon, Order, PricingPlan
from app.models.user import User
from app.schemas.admin import (
    AdminAdjustCreditsRequest,
    AdminAuditLogItem,
    AdminAuditLogResponse,
    AdminCouponCreateRequest,
    AdminCouponResponse,
    AdminCouponUpdateRequest,
    AdminDailyMetric,
    AdminDashboardStats,
    AdminImpersonateResponse,
    AdminJobListItem,
    AdminJobListResponse,
    AdminOrderListItem,
    AdminOrderListResponse,
    AdminUpdateSettingsRequest,
    AdminUpdateUserRoleRequest,
    AdminUpdateUserStatusRequest,
    AdminUpdateVoiceRequest,
    AdminUserDetail,
    AdminUserListItem,
    AdminUserListResponse,
    AdminVoiceListItem,
    AdminWithdrawalActionRequest,
    AdminWithdrawalItem,
)
from app.services.admin_audit_service import AdminAuditService
from app.services.credit_service import CreditService
from app.services.tts_job_service import TTSJobService
from app.services.tts_service import TTSService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin Portal"])


_get_client_ip = get_client_ip


# =============================================================
# 1. Dashboard Tổng quan (Analytics & Metrics)
# =============================================================
@router.get("/dashboard/stats", response_model=AdminDashboardStats, summary="Thống kê tổng quan hệ thống")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    now = datetime.now(UTC)
    today_start = datetime(now.year, now.month, now.day, tzinfo=UTC)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = datetime(now.year, now.month, 1, tzinfo=UTC)

    # 1. Người dùng
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    new_users_today = (await db.execute(select(func.count(User.id)).where(User.created_at >= today_start))).scalar() or 0
    new_users_this_week = (await db.execute(select(func.count(User.id)).where(User.created_at >= week_start))).scalar() or 0
    new_users_this_month = (await db.execute(select(func.count(User.id)).where(User.created_at >= month_start))).scalar() or 0

    # 2. Doanh thu (Đơn hàng đã thanh toán status='paid')
    total_rev = (await db.execute(select(func.coalesce(func.sum(Order.final_amount), 0)).where(Order.status == "paid"))).scalar() or 0
    rev_today = (await db.execute(select(func.coalesce(func.sum(Order.final_amount), 0)).where(Order.status == "paid", Order.created_at >= today_start))).scalar() or 0
    rev_month = (await db.execute(select(func.coalesce(func.sum(Order.final_amount), 0)).where(Order.status == "paid", Order.created_at >= month_start))).scalar() or 0

    # 3. Ký tự & Jobs
    total_chars = (await db.execute(select(func.coalesce(func.sum(Generation.char_count), 0)))).scalar() or 0
    chars_today = (await db.execute(select(func.coalesce(func.sum(Generation.char_count), 0)).where(Generation.created_at >= today_start))).scalar() or 0

    total_jobs = (await db.execute(select(func.count(Generation.id)))).scalar() or 0
    failed_jobs = (await db.execute(select(func.count(Generation.id)).where(Generation.status == "failed"))).scalar() or 0
    failure_rate = round((failed_jobs / total_jobs * 100), 2) if total_jobs > 0 else 0.0

    # 4. Ước tính chi phí provider (0.2 VND/char cho Edge/Mock/ElevenLabs trung bình)
    provider_cost_today = round(chars_today * 0.15, 2)
    chars_month = (await db.execute(select(func.coalesce(func.sum(Generation.char_count), 0)).where(Generation.created_at >= month_start))).scalar() or 0
    provider_cost_month = round(chars_month * 0.15, 2)

    # 5. Dữ liệu 7 ngày gần nhất
    daily_metrics: List[AdminDailyMetric] = []
    for day_offset in range(6, -1, -1):
        target_day = today_start - timedelta(days=day_offset)
        next_day = target_day + timedelta(days=1)
        day_str = target_day.strftime("%d/%m")

        u_day = (await db.execute(select(func.count(User.id)).where(User.created_at >= target_day, User.created_at < next_day))).scalar() or 0
        r_day = (await db.execute(select(func.coalesce(func.sum(Order.final_amount), 0)).where(Order.status == "paid", Order.created_at >= target_day, Order.created_at < next_day))).scalar() or 0
        c_day = (await db.execute(select(func.coalesce(func.sum(Generation.char_count), 0)).where(Generation.created_at >= target_day, Generation.created_at < next_day))).scalar() or 0
        j_day = (await db.execute(select(func.count(Generation.id)).where(Generation.created_at >= target_day, Generation.created_at < next_day))).scalar() or 0
        fj_day = (await db.execute(select(func.count(Generation.id)).where(Generation.status == "failed", Generation.created_at >= target_day, Generation.created_at < next_day))).scalar() or 0

        daily_metrics.append(AdminDailyMetric(
            date=day_str,
            new_users=u_day,
            revenue=r_day,
            characters=c_day,
            jobs_count=j_day,
            failed_jobs=fj_day,
        ))

    return AdminDashboardStats(
        total_users=total_users,
        new_users_today=new_users_today,
        new_users_this_week=new_users_this_week,
        new_users_this_month=new_users_this_month,
        total_revenue=total_rev,
        revenue_today=rev_today,
        revenue_this_month=rev_month,
        total_characters=total_chars,
        characters_today=chars_today,
        total_jobs=total_jobs,
        failed_jobs=failed_jobs,
        failure_rate_percent=failure_rate,
        provider_cost_today_estimated=provider_cost_today,
        provider_cost_month_estimated=provider_cost_month,
        daily_metrics=daily_metrics,
    )


# =============================================================
# 2. Quản lý Người dùng (Users)
# =============================================================
@router.get("/users", response_model=AdminUserListResponse, summary="Danh sách người dùng có tìm kiếm và phân trang")
async def list_users(
    q: Optional[str] = Query(None, description="Tìm theo email hoặc họ tên"),
    role: Optional[str] = Query(None, description="Lọc theo role"),
    is_active: Optional[bool] = Query(None, description="Lọc trạng thái hoạt động"),
    tier: Optional[str] = Query(None, description="Lọc gói cước"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    stmt = select(User)
    count_stmt = select(func.count(User.id))

    if q:
        term = f"%{q.strip()}%"
        cond = or_(User.email.ilike(term), User.full_name.ilike(term))
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    if role:
        stmt = stmt.where(User.role == role)
        count_stmt = count_stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
        count_stmt = count_stmt.where(User.is_active == is_active)
    if tier:
        stmt = stmt.where(User.subscription_tier == tier)
        count_stmt = count_stmt.where(User.subscription_tier == tier)

    total = (await db.execute(count_stmt)).scalar() or 0
    p = page if isinstance(page, int) else 1
    page_size = limit if isinstance(limit, int) else 20
    offset = (p - 1) * page_size
    stmt = stmt.order_by(desc(User.created_at)).offset(offset).limit(page_size)
    users = list((await db.execute(stmt)).scalars().all())

    items: List[AdminUserListItem] = []
    for u in users:
        # Đếm tổng jobs và chi tiêu
        j_cnt = (await db.execute(select(func.count(Generation.id)).where(Generation.user_id == u.id))).scalar() or 0
        spent_sum = (await db.execute(select(func.coalesce(func.sum(Order.final_amount), 0)).where(Order.user_id == u.id, Order.status == "paid"))).scalar() or 0
        items.append(AdminUserListItem(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            subscription_tier=u.subscription_tier,
            is_active=u.is_active,
            is_admin=u.is_admin,
            is_verified=u.is_verified,
            credit_balance=u.credit_balance,
            total_jobs=j_cnt,
            total_spent=spent_sum,
            created_at=u.created_at,
        ))

    total_pages = max(1, (total + page_size - 1) // page_size)
    return AdminUserListResponse(
        items=items,
        total=total,
        page=p,
        limit=page_size,
        total_pages=total_pages,
    )


@router.get("/users/{user_id}", response_model=AdminUserDetail, summary="Xem chi tiết hồ sơ người dùng")
async def get_user_detail(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    j_cnt = (await db.execute(select(func.count(Generation.id)).where(Generation.user_id == user.id))).scalar() or 0
    spent_sum = (await db.execute(select(func.coalesce(func.sum(Order.final_amount), 0)).where(Order.user_id == user.id, Order.status == "paid"))).scalar() or 0

    # 10 giao dịch gần nhất
    txs = list((await db.execute(
        select(CreditTransaction).where(CreditTransaction.user_id == user.id).order_by(desc(CreditTransaction.created_at)).limit(10)
    )).scalars().all())
    recent_txs = [
        {
            "id": t.id,
            "amount": t.amount,
            "type": t.type or t.tx_type,
            "balance_after": t.balance_after,
            "description": t.description,
            "created_at": t.created_at.isoformat(),
        }
        for t in txs
    ]

    # 10 job gần nhất
    gens = list((await db.execute(
        select(Generation).where(Generation.user_id == user.id).order_by(desc(Generation.created_at)).limit(10)
    )).scalars().all())
    recent_jobs = [
        {
            "id": g.id,
            "text": g.text[:80] + "..." if len(g.text) > 80 else g.text,
            "voice": g.voice,
            "status": g.status,
            "char_count": g.char_count,
            "duration": g.duration,
            "created_at": g.created_at.isoformat(),
        }
        for g in gens
    ]

    return AdminUserDetail(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        subscription_tier=user.subscription_tier,
        is_active=user.is_active,
        is_admin=user.is_admin,
        is_verified=user.is_verified,
        credit_balance=user.credit_balance,
        credits=user.credits,
        google_id=user.google_id,
        created_at=user.created_at,
        updated_at=user.updated_at,
        total_jobs=j_cnt,
        total_spent=spent_sum,
        recent_transactions=recent_txs,
        recent_jobs=recent_jobs,
    )


@router.post("/users/{user_id}/credits", summary="Cộng / trừ credit thủ công (ghi thẳng vào sổ cái ledger)")
async def adjust_user_credits(
    user_id: int,
    body: AdminAdjustCreditsRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    old_balance = user.credit_balance
    tx = await CreditService.add_adjustment(
        db=db,
        user_id=user_id,
        amount=body.amount,
        tx_type=CreditTransactionType.ADMIN_ADJUST.value,
        description=f"[Admin #{admin.id} - {admin.email}] {body.reason}",
    )

    # Ghi nhận Audit Log
    await AdminAuditService.log_action(
        db=db,
        admin_id=admin.id,
        action="adjust_credits",
        target_type="user",
        target_id=str(user_id),
        details={
            "user_email": user.email,
            "amount": body.amount,
            "old_balance": old_balance,
            "new_balance": tx.balance_after,
            "reason": body.reason,
            "tx_id": tx.id,
        },
        ip_address=_get_client_ip(request),
    )

    return {
        "success": True,
        "user_id": user_id,
        "old_balance": old_balance,
        "new_balance": tx.balance_after,
        "adjusted_amount": body.amount,
        "transaction_id": tx.id,
        "reason": body.reason,
    }


@router.patch("/users/{user_id}/status", summary="Khóa / mở khóa tài khoản người dùng")
async def update_user_status(
    user_id: int,
    body: AdminUpdateUserStatusRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    if user_id == admin.id and not body.is_active:
        raise HTTPException(status_code=400, detail="Không thể tự khóa tài khoản quản trị của chính mình.")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    old_status = user.is_active
    user.is_active = body.is_active
    await db.commit()

    action_name = "unlock_user" if body.is_active else "lock_user"
    await AdminAuditService.log_action(
        db=db,
        admin_id=admin.id,
        action=action_name,
        target_type="user",
        target_id=str(user_id),
        details={
            "user_email": user.email,
            "old_is_active": old_status,
            "new_is_active": body.is_active,
            "reason": body.reason,
        },
        ip_address=_get_client_ip(request),
    )

    return {
        "success": True,
        "user_id": user_id,
        "is_active": user.is_active,
        "message": f"Đã {'mở khóa' if user.is_active else 'khóa'} tài khoản thành công.",
    }


@router.patch("/users/{user_id}/role", summary="Đổi role người dùng (user / admin)")
async def update_user_role(
    user_id: int,
    body: AdminUpdateUserRoleRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    if user_id == admin.id and body.role != "admin":
        raise HTTPException(status_code=400, detail="Không thể tự hạ quyền quản trị của chính mình.")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    old_role = user.role
    user.role = body.role
    user.is_admin = (body.role == "admin")
    await db.commit()

    await AdminAuditService.log_action(
        db=db,
        admin_id=admin.id,
        action="change_role",
        target_type="user",
        target_id=str(user_id),
        details={
            "user_email": user.email,
            "old_role": old_role,
            "new_role": body.role,
            "reason": body.reason,
        },
        ip_address=_get_client_ip(request),
    )

    return {
        "success": True,
        "user_id": user_id,
        "role": user.role,
        "is_admin": user.is_admin,
    }


@router.post("/users/{user_id}/impersonate", response_model=AdminImpersonateResponse, summary="Đăng nhập giả lập (impersonate) người dùng")
async def impersonate_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    # Sinh access token mạo danh có ghi nhận admin gốc
    token = create_access_token(data={
        "sub": str(user.id),
        "impersonated_by": str(admin.id),
    })

    await AdminAuditService.log_action(
        db=db,
        admin_id=admin.id,
        action="impersonate",
        target_type="user",
        target_id=str(user_id),
        details={"user_email": user.email, "target_user_id": user.id},
        ip_address=_get_client_ip(request),
    )

    return AdminImpersonateResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
    )


# =============================================================
# 3. Quản lý Jobs (TTS Generations)
# =============================================================
@router.get("/jobs", response_model=AdminJobListResponse, summary="Theo dõi danh sách Job xử lý toàn hệ thống")
async def list_jobs(
    status_filter: Optional[str] = Query(None, alias="status", description="Lọc trạng thái job: done, processing, failed, queued"),
    user_id: Optional[int] = Query(None, description="Lọc theo user ID"),
    q: Optional[str] = Query(None, description="Tìm theo nội dung văn bản"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    stmt = select(Generation, User.email.label("user_email")).outerjoin(User, Generation.user_id == User.id)
    count_stmt = select(func.count(Generation.id))

    if status_filter and isinstance(status_filter, str):
        stmt = stmt.where(Generation.status == status_filter)
        count_stmt = count_stmt.where(Generation.status == status_filter)
    if user_id and isinstance(user_id, int):
        stmt = stmt.where(Generation.user_id == user_id)
        count_stmt = count_stmt.where(Generation.user_id == user_id)
    if q and isinstance(q, str):
        stmt = stmt.where(Generation.text.ilike(f"%{q.strip()}%"))
        count_stmt = count_stmt.where(Generation.text.ilike(f"%{q.strip()}%"))

    total = (await db.execute(count_stmt)).scalar() or 0
    p = page if isinstance(page, int) else 1
    page_size = limit if isinstance(limit, int) else 20
    offset = (p - 1) * page_size
    stmt = stmt.order_by(desc(Generation.created_at)).offset(offset).limit(page_size)
    rows = (await db.execute(stmt)).all()

    items: List[AdminJobListItem] = []
    for gen, email in rows:
        items.append(AdminJobListItem(
            id=gen.id,
            user_id=gen.user_id,
            user_email=email,
            voice=gen.voice,
            char_count=gen.char_count,
            status=gen.status,
            progress=gen.progress,
            duration=gen.duration,
            credit_used=gen.credit_used,
            error_message=gen.error_message,
            format=gen.format,
            created_at=gen.created_at,
            file_path=gen.file_path,
        ))

    total_pages = max(1, (total + page_size - 1) // page_size)
    return AdminJobListResponse(
        items=items,
        total=total,
        page=p,
        limit=page_size,
        total_pages=total_pages,
    )


@router.post("/jobs/{job_id}/retry", summary="Chạy lại job lỗi")
async def retry_job(
    job_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
    tts_service: TTSService = Depends(get_tts_service),
):
    job = (await db.execute(select(Generation).where(Generation.id == job_id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy Job.")

    old_status = job.status
    job.status = "queued"
    job.progress = 0
    job.error_message = None
    await db.commit()

    # Kích hoạt chạy lại background
    job_service = TTSJobService(tts_service=tts_service)
    asyncio.create_task(job_service._execute_job_in_background(job.id, apply_dict=getattr(job, "apply_dictionary", True)))

    await AdminAuditService.log_action(
        db=db,
        admin_id=admin.id,
        action="retry_job",
        target_type="job",
        target_id=str(job_id),
        details={"job_id": job_id, "old_status": old_status, "voice": job.voice, "user_id": job.user_id},
        ip_address=_get_client_ip(request),
    )

    return {"success": True, "job_id": job_id, "status": "queued", "message": "Đã xếp hàng chạy lại Job thành công."}


@router.post("/jobs/{job_id}/refund", summary="Hoàn credit thủ công cho Job")
async def refund_job(
    job_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    job = (await db.execute(select(Generation).where(Generation.id == job_id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy Job.")

    if not job.user_id:
        raise HTTPException(status_code=400, detail="Job không gắn với người dùng cụ thể để hoàn tiền.")

    if job.credit_used <= 0:
        raise HTTPException(status_code=400, detail="Job này không tiêu tốn credit nào.")

    # Kiểm tra đã hoàn chưa
    refund_ref = f"admin_refund_job_{job_id}"
    existing_rf = (await db.execute(select(CreditTransaction).where(CreditTransaction.ref_id == refund_ref))).scalar_one_or_none()
    if existing_rf:
        raise HTTPException(status_code=400, detail="Job này đã được hoàn credit trước đó rồi.")

    tx = await CreditService.refund(
        db=db,
        user_id=job.user_id,
        amount=job.credit_used,
        ref_id=refund_ref,
        reason=f"Admin #{admin.id} hoàn credit thủ công cho Job #{job_id}",
    )

    await AdminAuditService.log_action(
        db=db,
        admin_id=admin.id,
        action="refund_job",
        target_type="job",
        target_id=str(job_id),
        details={"job_id": job_id, "user_id": job.user_id, "amount": job.credit_used, "tx_id": tx.id},
        ip_address=_get_client_ip(request),
    )

    return {
        "success": True,
        "job_id": job_id,
        "user_id": job.user_id,
        "refunded_amount": job.credit_used,
        "balance_after": tx.balance_after,
    }


# =============================================================
# 4. Quản lý Giọng đọc (Voices)
# =============================================================
@router.get("/voices", response_model=List[AdminVoiceListItem], summary="Danh sách giọng đọc hệ thống và cấu hình quản trị")
async def list_admin_voices(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
    tts_service: TTSService = Depends(get_tts_service),
):
    provider_voices = await tts_service.get_voices(force_refresh=False)
    # Lấy toàn bộ override từ DB
    settings_records = list((await db.execute(select(SystemVoiceSetting))).scalars().all())
    settings_map = {s.voice_id: s for s in settings_records}

    result: List[AdminVoiceListItem] = []
    for pv in provider_voices:
        vid = pv["id"]
        cfg = settings_map.get(vid)
        result.append(AdminVoiceListItem(
            voice_id=vid,
            name=cfg.name if (cfg and cfg.name) else pv.get("name", vid),
            gender=pv.get("gender", "Unknown"),
            locale=pv.get("locale", "vi-VN"),
            is_vietnamese=pv.get("is_vietnamese", True),
            is_active=cfg.is_active if cfg else True,
            tier=cfg.tier if cfg else "free",
            credit_multiplier=cfg.credit_multiplier if cfg else 1.0,
        ))

    return result


@router.put("/voices/{voice_id}", response_model=AdminVoiceListItem, summary="Cập nhật cấu hình giọng đọc (bật/tắt, nhãn, hệ số nhân credit)")
async def update_voice_setting(
    voice_id: str,
    body: AdminUpdateVoiceRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    cfg = (await db.execute(select(SystemVoiceSetting).where(SystemVoiceSetting.voice_id == voice_id))).scalar_one_or_none()
    if not cfg:
        cfg = SystemVoiceSetting(voice_id=voice_id)
        db.add(cfg)

    old_data = {"is_active": cfg.is_active, "tier": cfg.tier, "credit_multiplier": cfg.credit_multiplier, "name": cfg.name}

    if body.is_active is not None:
        cfg.is_active = body.is_active
    if body.tier is not None:
        cfg.tier = body.tier
    if body.credit_multiplier is not None:
        cfg.credit_multiplier = body.credit_multiplier
    if body.name is not None:
        cfg.name = body.name

    await db.commit()
    await db.refresh(cfg)

    await AdminAuditService.log_action(
        db=db,
        admin_id=admin.id,
        action="update_voice",
        target_type="voice",
        target_id=voice_id,
        details={"voice_id": voice_id, "old": old_data, "new": {"is_active": cfg.is_active, "tier": cfg.tier, "credit_multiplier": cfg.credit_multiplier, "name": cfg.name}},
        ip_address=_get_client_ip(request),
    )

    return AdminVoiceListItem(
        voice_id=cfg.voice_id,
        name=cfg.name or cfg.voice_id,
        is_active=cfg.is_active,
        tier=cfg.tier,
        credit_multiplier=cfg.credit_multiplier,
    )


# =============================================================
# 5. Quản lý Kinh doanh (Coupons, Orders, Affiliate Withdrawals)
# =============================================================
@router.get("/coupons", response_model=List[AdminCouponResponse], summary="Danh sách mã coupon giảm giá")
async def list_admin_coupons(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    coupons = list((await db.execute(select(Coupon).order_by(desc(Coupon.created_at)))).scalars().all())
    return [
        AdminCouponResponse(
            id=c.id,
            code=c.code,
            discount_percent=c.discount_value if c.discount_type == "percent" else None,
            discount_amount=c.discount_value if c.discount_type == "fixed" else None,
            max_uses=c.max_uses,
            used_count=c.used_count,
            is_active=c.is_active,
            expires_at=c.expires_at,
            created_at=c.created_at,
        )
        for c in coupons
    ]


@router.post("/coupons", response_model=AdminCouponResponse, status_code=status.HTTP_201_CREATED, summary="Tạo mã coupon giảm giá mới")
async def create_coupon(
    body: AdminCouponCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    code_upper = body.code.strip().upper()
    existing = (await db.execute(select(Coupon).where(Coupon.code == code_upper))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Mã coupon này đã tồn tại.")

    disc_type = "percent" if body.discount_percent is not None else "fixed"
    disc_val = body.discount_percent if body.discount_percent is not None else (body.discount_amount or 0)

    coupon = Coupon(
        code=code_upper,
        discount_type=disc_type,
        discount_value=disc_val,
        max_uses=body.max_uses,
        expires_at=body.expires_at,
        is_active=body.is_active,
    )
    db.add(coupon)
    await db.commit()
    await db.refresh(coupon)

    await AdminAuditService.log_action(
        db=db,
        admin_id=admin.id,
        action="create_coupon",
        target_type="coupon",
        target_id=str(coupon.id),
        details={"code": coupon.code, "discount_type": coupon.discount_type, "discount_value": coupon.discount_value},
        ip_address=_get_client_ip(request),
    )

    return AdminCouponResponse(
        id=coupon.id,
        code=coupon.code,
        discount_percent=coupon.discount_value if coupon.discount_type == "percent" else None,
        discount_amount=coupon.discount_value if coupon.discount_type == "fixed" else None,
        max_uses=coupon.max_uses,
        used_count=coupon.used_count,
        is_active=coupon.is_active,
        expires_at=coupon.expires_at,
        created_at=coupon.created_at,
    )


@router.put("/coupons/{coupon_id}", response_model=AdminCouponResponse, summary="Chỉnh sửa mã coupon")
async def update_coupon(
    coupon_id: int,
    body: AdminCouponUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    coupon = (await db.execute(select(Coupon).where(Coupon.id == coupon_id))).scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=404, detail="Không tìm thấy coupon.")

    if body.discount_percent is not None:
        coupon.discount_type = "percent"
        coupon.discount_value = body.discount_percent
    elif body.discount_amount is not None:
        coupon.discount_type = "fixed"
        coupon.discount_value = body.discount_amount
    if body.max_uses is not None:
        coupon.max_uses = body.max_uses
    if body.expires_at is not None:
        coupon.expires_at = body.expires_at
    if body.is_active is not None:
        coupon.is_active = body.is_active

    await db.commit()
    await db.refresh(coupon)

    await AdminAuditService.log_action(
        db=db,
        admin_id=admin.id,
        action="update_coupon",
        target_type="coupon",
        target_id=str(coupon.id),
        details={"code": coupon.code, "is_active": coupon.is_active},
        ip_address=_get_client_ip(request),
    )

    return AdminCouponResponse(
        id=coupon.id,
        code=coupon.code,
        discount_percent=coupon.discount_value if coupon.discount_type == "percent" else None,
        discount_amount=coupon.discount_value if coupon.discount_type == "fixed" else None,
        max_uses=coupon.max_uses,
        used_count=coupon.used_count,
        is_active=coupon.is_active,
        expires_at=coupon.expires_at,
        created_at=coupon.created_at,
    )


@router.delete("/coupons/{coupon_id}", summary="Xóa mã coupon")
async def delete_coupon(
    coupon_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    coupon = (await db.execute(select(Coupon).where(Coupon.id == coupon_id))).scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=404, detail="Không tìm thấy coupon.")

    code = coupon.code
    await db.delete(coupon)
    await db.commit()

    await AdminAuditService.log_action(
        db=db,
        admin_id=admin.id,
        action="delete_coupon",
        target_type="coupon",
        target_id=str(coupon_id),
        details={"code": code},
        ip_address=_get_client_ip(request),
    )

    return {"success": True, "message": f"Đã xóa mã coupon {code}."}


@router.get("/orders", response_model=AdminOrderListResponse, summary="Danh sách đơn hàng thanh toán toàn hệ thống")
async def list_admin_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    q: Optional[str] = Query(None, description="Tìm theo mã đơn hàng"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    stmt = (
        select(Order, User.email.label("user_email"), PricingPlan.name.label("plan_name"))
        .join(User, Order.user_id == User.id)
        .outerjoin(PricingPlan, Order.plan_id == PricingPlan.id)
    )
    count_stmt = select(func.count(Order.id))

    if status_filter and isinstance(status_filter, str):
        stmt = stmt.where(Order.status == status_filter)
        count_stmt = count_stmt.where(Order.status == status_filter)
    if q and isinstance(q, str):
        stmt = stmt.where(Order.order_code.ilike(f"%{q.strip()}%"))
        count_stmt = count_stmt.where(Order.order_code.ilike(f"%{q.strip()}%"))

    total = (await db.execute(count_stmt)).scalar() or 0
    p = page if isinstance(page, int) else 1
    page_size = limit if isinstance(limit, int) else 20
    offset = (p - 1) * page_size
    stmt = stmt.order_by(desc(Order.created_at)).offset(offset).limit(page_size)
    rows = (await db.execute(stmt)).all()

    items: List[AdminOrderListItem] = []
    for o, u_email, p_name in rows:
        items.append(AdminOrderListItem(
            id=o.id,
            order_code=o.order_code,
            user_id=o.user_id,
            user_email=u_email,
            plan_name=p_name,
            original_amount=o.original_amount,
            final_amount=o.final_amount,
            credits_to_add=o.credits_to_add,
            payment_method=o.payment_method,
            status=o.status,
            created_at=o.created_at,
        ))

    total_pages = max(1, (total + page_size - 1) // page_size)
    return AdminOrderListResponse(
        items=items,
        total=total,
        page=p,
        limit=page_size,
        total_pages=total_pages,
    )


@router.post("/orders/{order_id}/approve", summary="Xác nhận thanh toán thủ công đơn hàng (nạp credit)")
async def manual_approve_order(
    order_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    from app.services.payment_service import PaymentService

    order = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")

    if order.status == "paid":
        raise HTTPException(status_code=400, detail="Đơn hàng đã được thanh toán thành công trước đó.")

    # Xử lý hoàn tất đơn hàng qua PaymentService
    await PaymentService.process_successful_payment(
        db=db,
        order=order,
        gateway="manual_admin",
        transaction_id=f"admin_{admin.id}_{int(datetime.now(UTC).timestamp())}",
        paid_amount=order.final_amount,
    )

    await AdminAuditService.log_action(
        db=db,
        admin_id=admin.id,
        action="approve_order",
        target_type="order",
        target_id=str(order_id),
        details={"order_code": order.order_code, "final_amount": order.final_amount, "credits": order.credits_to_add},
        ip_address=_get_client_ip(request),
    )

    return {"success": True, "order_id": order_id, "order_code": order.order_code, "status": "paid"}


@router.get("/affiliates/withdrawals", response_model=List[AdminWithdrawalItem], summary="Danh sách yêu cầu rút tiền Affiliate")
async def list_affiliate_withdrawals(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    stmt = select(AffiliateWithdrawal, User.email.label("user_email")).join(User, AffiliateWithdrawal.user_id == User.id)
    if status_filter and isinstance(status_filter, str):
        stmt = stmt.where(AffiliateWithdrawal.status == status_filter)

    rows = (await db.execute(stmt.order_by(desc(AffiliateWithdrawal.created_at)))).all()
    return [
        AdminWithdrawalItem(
            id=w.id,
            user_id=w.user_id,
            user_email=email,
            amount=w.amount,
            bank_name=w.bank_name,
            bank_account_number=w.bank_account_number,
            bank_account_holder=w.bank_account_holder,
            status=w.status,
            note=w.note,
            created_at=w.created_at,
            updated_at=w.updated_at,
        )
        for w, email in rows
    ]


@router.post("/affiliates/withdrawals/{w_id}/approve", summary="Duyệt yêu cầu rút tiền Affiliate")
async def approve_affiliate_withdrawal(
    w_id: int,
    body: AdminWithdrawalActionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    w = (await db.execute(select(AffiliateWithdrawal).where(AffiliateWithdrawal.id == w_id))).scalar_one_or_none()
    if not w:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu rút tiền.")
    if w.status != "pending":
        raise HTTPException(status_code=400, detail="Yêu cầu này đã được xử lý trước đó.")

    w.status = "approved"
    if body.note:
        w.note = body.note
    await db.commit()

    await AdminAuditService.log_action(
        db=db,
        admin_id=admin.id,
        action="approve_withdrawal",
        target_type="withdrawal",
        target_id=str(w_id),
        details={"user_id": w.user_id, "amount": w.amount, "note": body.note},
        ip_address=_get_client_ip(request),
    )

    return {"success": True, "id": w_id, "status": "approved"}


@router.post("/affiliates/withdrawals/{w_id}/reject", summary="Từ chối yêu cầu rút tiền Affiliate")
async def reject_affiliate_withdrawal(
    w_id: int,
    body: AdminWithdrawalActionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    w = (await db.execute(select(AffiliateWithdrawal).where(AffiliateWithdrawal.id == w_id))).scalar_one_or_none()
    if not w:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu rút tiền.")
    if w.status != "pending":
        raise HTTPException(status_code=400, detail="Yêu cầu này đã được xử lý trước đó.")

    w.status = "rejected"
    w.note = body.note or "Yêu cầu bị từ chối bởi Quản trị viên"
    await db.commit()

    await AdminAuditService.log_action(
        db=db,
        admin_id=admin.id,
        action="reject_withdrawal",
        target_type="withdrawal",
        target_id=str(w_id),
        details={"user_id": w.user_id, "amount": w.amount, "reason": w.note},
        ip_address=_get_client_ip(request),
    )

    return {"success": True, "id": w_id, "status": "rejected"}


# =============================================================
# 6. Cài đặt hệ thống & Nhật ký Audit Log
# =============================================================
@router.get("/settings", summary="Lấy danh sách các cài đặt hệ thống")
async def get_system_settings(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    from app.config import get_settings
    settings = get_settings()

    db_settings = list((await db.execute(select(SystemSetting))).scalars().all())
    res_map: Dict[str, Any] = {
        "signup_bonus_credits": str(getattr(settings, "credit_signup_bonus", 10000)),
        "max_chars": str(settings.max_chars),
        "tts_provider": settings.tts_provider,
        "clone_provider": getattr(settings, "clone_provider", "mock"),
        "require_email_verification": str(getattr(settings, "require_email_verification", False)).lower(),
        "maintenance_mode": "false",
    }
    for item in db_settings:
        res_map[item.key] = item.value

    return res_map


@router.put("/settings", summary="Cập nhật cấu hình hệ thống")
async def update_system_settings(
    body: AdminUpdateSettingsRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    updated_keys = []
    for k, v in body.settings.items():
        record = (await db.execute(select(SystemSetting).where(SystemSetting.key == k))).scalar_one_or_none()
        if not record:
            record = SystemSetting(key=k, value=str(v))
            db.add(record)
        else:
            record.value = str(v)
        updated_keys.append(k)

    await db.commit()

    await AdminAuditService.log_action(
        db=db,
        admin_id=admin.id,
        action="update_settings",
        target_type="setting",
        target_id="global",
        details={"updated_settings": body.settings},
        ip_address=_get_client_ip(request),
    )

    return {"success": True, "updated_keys": updated_keys}


@router.get("/audit-logs", response_model=AdminAuditLogResponse, summary="Xem nhật ký hoạt động của Quản trị viên (Audit Log)")
async def get_audit_logs(
    action: Optional[str] = Query(None, description="Lọc theo hành động"),
    target_type: Optional[str] = Query(None, description="Lọc theo đối tượng tác động"),
    admin_id: Optional[int] = Query(None, description="Lọc theo Admin ID"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    p = page if isinstance(page, int) else 1
    page_size = limit if isinstance(limit, int) else 20
    items, total = await AdminAuditService.list_logs(
        db=db,
        action=action,
        target_type=target_type,
        admin_id=admin_id,
        page=p,
        limit=page_size,
    )

    result_items: List[AdminAuditLogItem] = []
    for it in items:
        details_obj: Optional[Dict[str, Any]] = None
        if it.details:
            try:
                details_obj = json.loads(it.details)
            except Exception:
                details_obj = {"raw": it.details}

        result_items.append(AdminAuditLogItem(
            id=it.id,
            admin_id=it.admin_id,
            admin_email=getattr(it, "admin_email", None),
            action=it.action,
            target_type=it.target_type,
            target_id=it.target_id,
            details=details_obj,
            ip_address=it.ip_address,
            created_at=it.created_at,
        ))

    total_pages = max(1, (total + page_size - 1) // page_size)
    return AdminAuditLogResponse(
        items=result_items,
        total=total,
        page=p,
        limit=page_size,
        total_pages=total_pages,
    )
