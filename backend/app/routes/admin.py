"""Router API dành riêng cho Quản trị viên (Admin Portal - Issue #15, refactored in Issue #45)."""
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_client_ip
from app.db import get_db
from app.dependencies import get_current_admin_user, get_tts_service
from app.models.user import User
from app.schemas.admin import (
    AdminAdjustCreditsRequest,
    AdminAuditLogResponse,
    AdminCouponCreateRequest,
    AdminCouponResponse,
    AdminCouponUpdateRequest,
    AdminDashboardStats,
    AdminImpersonateResponse,
    AdminJobListResponse,
    AdminOrderListResponse,
    AdminUpdateSettingsRequest,
    AdminUpdateUserRoleRequest,
    AdminUpdateUserStatusRequest,
    AdminUpdateVoiceRequest,
    AdminUserDetail,
    AdminUserListResponse,
    AdminVoiceListItem,
    AdminWithdrawalActionRequest,
    AdminWithdrawalItem,
)
from app.services.admin_service import AdminService
from app.services.tts_service import TTSService

router = APIRouter(prefix="/api/admin", tags=["Admin Portal"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[User, Depends(get_current_admin_user)]
TTSDep = Annotated[TTSService, Depends(get_tts_service)]


# =============================================================
# 1. Dashboard Tổng quan (Analytics & Metrics)
# =============================================================
@router.get("/dashboard/stats", response_model=AdminDashboardStats, summary="Thống kê tổng quan hệ thống")
async def get_dashboard_stats(db: DbSession, admin: AdminUser):
    return await AdminService.get_dashboard_stats(db=db)


# =============================================================
# 2. Quản lý Người dùng (Users)
# =============================================================
@router.get("/users", response_model=AdminUserListResponse, summary="Danh sách người dùng có tìm kiếm và phân trang")
async def list_users(
    db: DbSession,
    admin: AdminUser,
    q: Optional[str] = Query(None, description="Tìm theo email hoặc họ tên"),
    role: Optional[str] = Query(None, description="Lọc theo role"),
    is_active: Optional[bool] = Query(None, description="Lọc trạng thái hoạt động"),
    tier: Optional[str] = Query(None, description="Lọc gói cước"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    return await AdminService.list_users(db=db, q=q, role=role, is_active=is_active, tier=tier, page=page, limit=limit)


@router.get("/users/{user_id}", response_model=AdminUserDetail, summary="Xem chi tiết hồ sơ người dùng")
async def get_user_detail(user_id: int, db: DbSession, admin: AdminUser):
    return await AdminService.get_user_detail(db=db, user_id=user_id)


@router.post("/users/{user_id}/credits", summary="Cộng / trừ credit thủ công (ghi thẳng vào sổ cái ledger)")
async def adjust_user_credits(user_id: int, body: AdminAdjustCreditsRequest, request: Request, db: DbSession, admin: AdminUser):
    return await AdminService.adjust_user_credits(
        db=db, admin=admin, user_id=user_id, body=body, ip_address=get_client_ip(request)
    )


@router.patch("/users/{user_id}/status", summary="Khóa / mở khóa tài khoản người dùng")
async def update_user_status(user_id: int, body: AdminUpdateUserStatusRequest, request: Request, db: DbSession, admin: AdminUser):
    return await AdminService.update_user_status(
        db=db, admin=admin, user_id=user_id, body=body, ip_address=get_client_ip(request)
    )


@router.patch("/users/{user_id}/role", summary="Đổi role người dùng (user / admin)")
async def update_user_role(user_id: int, body: AdminUpdateUserRoleRequest, request: Request, db: DbSession, admin: AdminUser):
    return await AdminService.update_user_role(
        db=db, admin=admin, user_id=user_id, body=body, ip_address=get_client_ip(request)
    )


@router.post("/users/{user_id}/impersonate", response_model=AdminImpersonateResponse, summary="Đăng nhập giả lập người dùng")
async def impersonate_user(user_id: int, request: Request, db: DbSession, admin: AdminUser):
    return await AdminService.impersonate_user(db=db, admin=admin, user_id=user_id, ip_address=get_client_ip(request))


# =============================================================
# 3. Quản lý Jobs (TTS Generations)
# =============================================================
@router.get("/jobs", response_model=AdminJobListResponse, summary="Theo dõi danh sách Job xử lý toàn hệ thống")
async def list_jobs(
    db: DbSession,
    admin: AdminUser,
    status_filter: Optional[str] = Query(None, alias="status", description="Lọc trạng thái job"),
    user_id: Optional[int] = Query(None, description="Lọc theo user ID"),
    q: Optional[str] = Query(None, description="Tìm theo nội dung văn bản"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    return await AdminService.list_jobs(db=db, status_filter=status_filter, user_id=user_id, q=q, page=page, limit=limit)


@router.post("/jobs/{job_id}/retry", summary="Chạy lại job lỗi")
async def retry_job(job_id: int, request: Request, db: DbSession, admin: AdminUser, tts_service: TTSDep):
    return await AdminService.retry_job(
        db=db, admin=admin, job_id=job_id, ip_address=get_client_ip(request), tts_service=tts_service
    )


@router.post("/jobs/{job_id}/refund", summary="Hoàn credit thủ công cho Job")
async def refund_job(job_id: int, request: Request, db: DbSession, admin: AdminUser):
    return await AdminService.refund_job(db=db, admin=admin, job_id=job_id, ip_address=get_client_ip(request))


# =============================================================
# 4. Quản lý Giọng đọc (Voices)
# =============================================================
@router.get("/voices", response_model=List[AdminVoiceListItem], summary="Danh sách giọng đọc hệ thống")
async def list_admin_voices(db: DbSession, admin: AdminUser, tts_service: TTSDep):
    return await AdminService.list_voices(db=db, tts_service=tts_service)


@router.put("/voices/{voice_id}", response_model=AdminVoiceListItem, summary="Cập nhật cấu hình giọng đọc")
async def update_voice_setting(voice_id: str, body: AdminUpdateVoiceRequest, request: Request, db: DbSession, admin: AdminUser):
    return await AdminService.update_voice_setting(
        db=db, admin=admin, voice_id=voice_id, body=body, ip_address=get_client_ip(request)
    )


# =============================================================
# 5. Quản lý Kinh doanh (Coupons, Orders, Affiliate Withdrawals)
# =============================================================
@router.get("/coupons", response_model=List[AdminCouponResponse], summary="Danh sách mã coupon giảm giá")
async def list_admin_coupons(db: DbSession, admin: AdminUser):
    return await AdminService.list_coupons(db=db)


@router.post("/coupons", response_model=AdminCouponResponse, status_code=status.HTTP_201_CREATED, summary="Tạo coupon mới")
async def create_coupon(body: AdminCouponCreateRequest, request: Request, db: DbSession, admin: AdminUser):
    return await AdminService.create_coupon(db=db, admin=admin, body=body, ip_address=get_client_ip(request))


@router.put("/coupons/{coupon_id}", response_model=AdminCouponResponse, summary="Chỉnh sửa mã coupon")
async def update_coupon(coupon_id: int, body: AdminCouponUpdateRequest, request: Request, db: DbSession, admin: AdminUser):
    return await AdminService.update_coupon(
        db=db, admin=admin, coupon_id=coupon_id, body=body, ip_address=get_client_ip(request)
    )


@router.delete("/coupons/{coupon_id}", summary="Xóa mã coupon")
async def delete_coupon(coupon_id: int, request: Request, db: DbSession, admin: AdminUser):
    return await AdminService.delete_coupon(db=db, admin=admin, coupon_id=coupon_id, ip_address=get_client_ip(request))


@router.get("/orders", response_model=AdminOrderListResponse, summary="Danh sách đơn hàng thanh toán")
async def list_admin_orders(
    db: DbSession,
    admin: AdminUser,
    status_filter: Optional[str] = Query(None, alias="status"),
    q: Optional[str] = Query(None, description="Tìm theo mã đơn hàng"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    return await AdminService.list_orders(db=db, status_filter=status_filter, q=q, page=page, limit=limit)


@router.post("/orders/{order_id}/approve", summary="Xác nhận thanh toán thủ công đơn hàng")
async def manual_approve_order(order_id: int, request: Request, db: DbSession, admin: AdminUser):
    return await AdminService.manual_approve_order(
        db=db, admin=admin, order_id=order_id, ip_address=get_client_ip(request)
    )


@router.get("/affiliates/withdrawals", response_model=List[AdminWithdrawalItem], summary="Danh sách rút tiền Affiliate")
async def list_affiliate_withdrawals(db: DbSession, admin: AdminUser, status_filter: Optional[str] = Query(None, alias="status")):
    return await AdminService.list_withdrawals(db=db, status_filter=status_filter)


@router.post("/affiliates/withdrawals/{w_id}/approve", summary="Duyệt yêu cầu rút tiền Affiliate")
async def approve_affiliate_withdrawal(
    w_id: int, body: AdminWithdrawalActionRequest, request: Request, db: DbSession, admin: AdminUser
):
    return await AdminService.approve_withdrawal(db=db, admin=admin, w_id=w_id, body=body, ip_address=get_client_ip(request))


@router.post("/affiliates/withdrawals/{w_id}/reject", summary="Từ chối yêu cầu rút tiền Affiliate")
async def reject_affiliate_withdrawal(
    w_id: int, body: AdminWithdrawalActionRequest, request: Request, db: DbSession, admin: AdminUser
):
    return await AdminService.reject_withdrawal(db=db, admin=admin, w_id=w_id, body=body, ip_address=get_client_ip(request))


# =============================================================
# 6. Cài đặt hệ thống & Nhật ký Audit Log
# =============================================================
@router.get("/settings", summary="Lấy danh sách các cài đặt hệ thống")
async def get_system_settings(db: DbSession, admin: AdminUser):
    return await AdminService.get_system_settings(db=db)


@router.put("/settings", summary="Cập nhật cấu hình hệ thống")
async def update_system_settings(body: AdminUpdateSettingsRequest, request: Request, db: DbSession, admin: AdminUser):
    return await AdminService.update_system_settings(
        db=db, admin=admin, body=body, ip_address=get_client_ip(request)
    )


@router.get("/audit-logs", response_model=AdminAuditLogResponse, summary="Xem nhật ký hoạt động của Admin")
async def get_audit_logs(
    db: DbSession,
    admin: AdminUser,
    action: Optional[str] = Query(None, description="Lọc theo hành động"),
    target_type: Optional[str] = Query(None, description="Lọc theo đối tượng tác động"),
    admin_id: Optional[int] = Query(None, description="Lọc theo Admin ID"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    return await AdminService.list_audit_logs(
        db=db, action=action, target_type=target_type, admin_id=admin_id, page=page, limit=limit
    )
