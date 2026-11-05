"""Pydantic schemas cho Thanh toán, Gói cước, Mã giảm giá, Đơn hàng."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

# --- Pricing Plan Schemas ---

class PricingPlanBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    type: str = Field(..., description="credit_pack | subscription")
    price: int = Field(..., ge=0, description="Giá bằng VND")
    currency: str = Field("VND", max_length=10)
    credits: int = Field(..., ge=0, description="Số lượng credit cộng vào")
    duration_days: int = Field(0, ge=0)
    storage_days: int = Field(7, ge=0)
    has_premium_voices: bool = False
    has_api_access: bool = False
    queue_priority: str = Field("standard", description="standard | high | ultra")
    concurrency_limit: int = Field(1, ge=1)
    badge: Optional[str] = None
    description: Optional[str] = None
    display_order: int = 0
    is_active: bool = True


class PricingPlanCreate(PricingPlanBase):
    pass


class PricingPlanUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[int] = Field(None, ge=0)
    credits: Optional[int] = Field(None, ge=0)
    duration_days: Optional[int] = None
    storage_days: Optional[int] = None
    has_premium_voices: Optional[bool] = None
    has_api_access: Optional[bool] = None
    queue_priority: Optional[str] = None
    concurrency_limit: Optional[int] = None
    badge: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class PricingPlanOut(PricingPlanBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Coupon Schemas ---

class CouponValidateRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    order_amount: int = Field(..., ge=0)


class CouponValidateResponse(BaseModel):
    valid: bool
    code: str
    discount_type: str
    discount_value: int
    discount_amount: int
    final_amount: int
    message: str


class CouponCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    discount_type: str = Field("percent", description="percent | fixed")
    discount_value: int = Field(..., gt=0)
    min_order_amount: int = Field(0, ge=0)
    max_uses: int = Field(100, gt=0)
    expires_at: Optional[datetime] = None
    is_active: bool = True


class CouponOut(BaseModel):
    id: int
    code: str
    discount_type: str
    discount_value: int
    min_order_amount: int
    max_uses: int
    used_count: int
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Order Schemas ---

class OrderCreateRequest(BaseModel):
    plan_id: int
    payment_method: str = Field("vietqr", description="vietqr | payos | stripe")
    coupon_code: Optional[str] = None


class OrderOut(BaseModel):
    id: int
    order_code: str
    order_number: int
    user_id: int
    plan_id: Optional[int]
    plan_name: Optional[str] = None
    plan_code: Optional[str] = None
    original_amount: int
    discount_amount: int
    final_amount: int
    credits_to_add: int
    payment_method: str
    status: str
    qr_url: Optional[str] = None
    checkout_url: Optional[str] = None
    transfer_content: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_no: Optional[str] = None
    bank_account_name: Optional[str] = None
    expires_at: datetime
    paid_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    orders: List[OrderOut]
    total: int
    page: int
    limit: int


class WebhookPayOSPayload(BaseModel):
    code: str
    desc: str
    data: dict
    signature: str


class WebhookSePayPayload(BaseModel):
    id: int
    gateway: str
    transactionDate: str
    accountNumber: str
    subAccount: Optional[str] = None
    transferType: str
    transferAmount: int
    accumulated: int
    code: Optional[str] = None
    content: Optional[str] = None
    referenceCode: Optional[str] = None
    description: Optional[str] = None


class SandboxPaymentSimulateRequest(BaseModel):
    order_id: int


class CardPaymentRequest(BaseModel):
    card_number: str = Field(..., min_length=12, max_length=24)
    exp_month: str = Field(..., min_length=1, max_length=2)
    exp_year: str = Field(..., min_length=2, max_length=4)
    cvc: str = Field(..., min_length=3, max_length=4)
    cardholder_name: str = Field(..., min_length=2, max_length=100)


class CardPaymentResult(BaseModel):
    order: OrderOut
    requires_otp: bool = True
    phone_hint: Optional[str] = "******899"
    expires_in: int = 180
    message: Optional[str] = "Ngân hàng phát hành yêu cầu xác thực 3D-Secure. Vui lòng nhập mã OTP."


class VerifyOtpRequest(BaseModel):
    otp: str = Field(..., min_length=4, max_length=8)


class ResendOtpResponse(BaseModel):
    success: bool = True
    message: str = "Đã gửi lại mã xác thực OTP mới."
    phone_hint: Optional[str] = "******899"
    expires_in: int = 180

