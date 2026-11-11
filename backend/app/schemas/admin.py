"""Pydantic schemas cho API Admin Portal (Issue #15)."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginatedResponse


# -------------------------------------------------------------
# 1. Dashboard Schemas
# -------------------------------------------------------------
class AdminDailyMetric(BaseModel):
    date: str
    new_users: int = 0
    revenue: int = 0
    characters: int = 0
    jobs_count: int = 0
    failed_jobs: int = 0


class AdminDashboardStats(BaseModel):
    total_users: int = 0
    new_users_today: int = 0
    new_users_this_week: int = 0
    new_users_this_month: int = 0

    total_revenue: int = 0
    revenue_today: int = 0
    revenue_this_month: int = 0

    total_characters: int = 0
    characters_today: int = 0

    total_jobs: int = 0
    failed_jobs: int = 0
    failure_rate_percent: float = 0.0

    provider_cost_today_estimated: float = 0.0
    provider_cost_month_estimated: float = 0.0

    daily_metrics: List[AdminDailyMetric] = []


# -------------------------------------------------------------
# 2. User Management Schemas
# -------------------------------------------------------------
class AdminUserListItem(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: str
    subscription_tier: str
    is_active: bool
    is_admin: bool
    is_verified: bool
    credit_balance: int
    total_jobs: int = 0
    total_spent: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUserListResponse(PaginatedResponse[AdminUserListItem]):
    """Danh sách người dùng có phân trang."""
    pass


class AdminUserDetail(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: str
    subscription_tier: str
    is_active: bool
    is_admin: bool
    is_verified: bool
    credit_balance: int
    credits: int
    google_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    total_jobs: int = 0
    total_spent: int = 0
    recent_transactions: List[Dict[str, Any]] = []
    recent_jobs: List[Dict[str, Any]] = []


class AdminAdjustCreditsRequest(BaseModel):
    amount: int = Field(..., description="Số credit muốn cộng (dương) hoặc trừ (âm)")
    reason: str = Field(..., min_length=3, max_length=500, description="Lý do điều chỉnh (bắt buộc ghi nhận sổ cái)")


class AdminUpdateUserStatusRequest(BaseModel):
    is_active: bool
    reason: Optional[str] = Field(None, max_length=500)


class AdminUpdateUserRoleRequest(BaseModel):
    role: str = Field(..., pattern="^(user|admin)$")
    reason: Optional[str] = Field(None, max_length=500)


class AdminImpersonateResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    full_name: Optional[str] = None
    role: str


# -------------------------------------------------------------
# 3. Job Management Schemas
# -------------------------------------------------------------
class AdminJobListItem(BaseModel):
    id: int
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    voice: str
    char_count: int
    status: str
    progress: int
    duration: float
    credit_used: int
    error_message: Optional[str] = None
    format: str
    created_at: datetime
    file_path: Optional[str] = None


class AdminJobListResponse(PaginatedResponse[AdminJobListItem]):
    """Danh sách job TTS & Audio tools của quản trị viên có phân trang."""
    pass


# -------------------------------------------------------------
# 4. Voice Management Schemas
# -------------------------------------------------------------
class AdminVoiceListItem(BaseModel):
    voice_id: str
    name: str
    gender: str = "Unknown"
    locale: str = "vi-VN"
    is_vietnamese: bool = True
    is_active: bool = True
    tier: str = "free"
    credit_multiplier: float = 1.0


class AdminUpdateVoiceRequest(BaseModel):
    is_active: Optional[bool] = None
    tier: Optional[str] = Field(None, pattern="^(free|premium)$")
    credit_multiplier: Optional[float] = Field(None, ge=0.1, le=10.0)
    name: Optional[str] = Field(None, min_length=1, max_length=150)


# -------------------------------------------------------------
# 5. Business Management Schemas (Coupons, Orders, Withdrawals)
# -------------------------------------------------------------
class AdminCouponCreateRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    discount_percent: Optional[int] = Field(None, ge=1, le=100)
    discount_amount: Optional[int] = Field(None, ge=1000)
    max_uses: Optional[int] = Field(None, ge=1)
    expires_at: Optional[datetime] = None
    is_active: bool = True


class AdminCouponUpdateRequest(BaseModel):
    discount_percent: Optional[int] = Field(None, ge=1, le=100)
    discount_amount: Optional[int] = Field(None, ge=1000)
    max_uses: Optional[int] = Field(None, ge=1)
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class AdminCouponResponse(BaseModel):
    id: int
    code: str
    discount_percent: Optional[int] = None
    discount_amount: Optional[int] = None
    max_uses: Optional[int] = None
    used_count: int = 0
    is_active: bool
    expires_at: Optional[datetime] = None
    created_at: datetime


class AdminOrderListItem(BaseModel):
    id: int
    order_code: str
    user_id: int
    user_email: Optional[str] = None
    plan_name: Optional[str] = None
    original_amount: int
    final_amount: int
    credits_to_add: int
    payment_method: Optional[str] = None
    status: str
    created_at: datetime


class AdminOrderListResponse(PaginatedResponse[AdminOrderListItem]):
    """Danh sách đơn hàng quản trị có phân trang."""
    pass


class AdminWithdrawalItem(BaseModel):
    id: int
    user_id: int
    user_email: Optional[str] = None
    amount: int
    bank_name: str
    bank_account_number: str
    bank_account_holder: str
    status: str
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AdminWithdrawalActionRequest(BaseModel):
    note: Optional[str] = Field(None, max_length=500)


# -------------------------------------------------------------
# 6. Settings & Audit Log Schemas
# -------------------------------------------------------------
class AdminUpdateSettingsRequest(BaseModel):
    settings: Dict[str, str] = Field(..., description="Cặp key-value các cấu hình hệ thống")


class AdminAuditLogItem(BaseModel):
    id: int
    admin_id: Optional[int] = None
    admin_email: Optional[str] = None
    action: str
    target_type: str
    target_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime


class AdminAuditLogResponse(PaginatedResponse[AdminAuditLogItem]):
    """Danh sách nhật ký can thiệp quản trị có phân trang."""
    pass
