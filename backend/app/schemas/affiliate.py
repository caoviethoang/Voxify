"""Pydantic schemas cho Chương trình Tiếp thị liên kết (Affiliate Program - Issue #14)."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AffiliateStats(BaseModel):
    total_clicks: int = 0
    total_signups: int = 0
    total_orders: int = 0
    pending_commission: int = 0
    available_commission: int = 0
    withdrawn_commission: int = 0
    total_earned_commission: int = 0


class AffiliateCommissionItem(BaseModel):
    id: int
    order_code: str
    buyer_masked_email: str
    order_amount: int
    commission_rate: float
    amount: int
    status: str
    hold_until: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AffiliateWithdrawalItem(BaseModel):
    id: int
    amount: int
    bank_name: str
    bank_account_number: str
    bank_account_holder: str
    status: str
    note: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AffiliateDashboardResponse(BaseModel):
    referral_code: str
    referral_link: str
    commission_rate: float
    hold_period_days: int
    min_payout_amount: int
    stats: AffiliateStats
    commissions: List[AffiliateCommissionItem] = []
    withdrawals: List[AffiliateWithdrawalItem] = []


class AffiliateWithdrawalRequest(BaseModel):
    amount: int = Field(..., ge=10000, description="Số tiền muốn rút (VNĐ)")
    bank_name: str = Field(..., min_length=2, max_length=100, description="Tên ngân hàng")
    bank_account_number: str = Field(..., min_length=3, max_length=50, description="Số tài khoản ngân hàng")
    bank_account_holder: str = Field(..., min_length=2, max_length=150, description="Tên chủ tài khoản")


class AffiliateTrackResponse(BaseModel):
    success: bool
    referral_code: str
    message: str


class AffiliateCustomizeCodeRequest(BaseModel):
    referral_code: str = Field(..., min_length=4, max_length=20, description="Mã giới thiệu mới (4-20 ký tự)")


class AffiliateCustomizeCodeResponse(BaseModel):
    success: bool
    referral_code: str
    referral_link: str
    message: str
