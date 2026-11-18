"""Models cho Chương trình Tiếp thị liên kết (Affiliate Program - Issue #14)."""
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, CreatedAtMixin, TimestampMixin


class CommissionStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    CANCELLED = "cancelled"


class WithdrawalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AffiliateCommission(Base, TimestampMixin):
    """Bản ghi hoa hồng chia sẻ cho người giới thiệu."""
    __tablename__ = "affiliate_commissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    affiliate_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    referred_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    order_amount: Mapped[int] = mapped_column(Integer, nullable=False)  # VND
    commission_rate: Mapped[float] = mapped_column(Float, nullable=False)  # Ví dụ 0.25 (25%)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # Hoa hồng VND
    status: Mapped[str] = mapped_column(
        String(20), default=CommissionStatus.PENDING.value, nullable=False, index=True
    )  # pending | approved | cancelled
    hold_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )  # Thời điểm hết hạn tạm giữ (14 ngày)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    affiliate_user: Mapped["User"] = relationship(
        "User", foreign_keys=[affiliate_user_id], back_populates="affiliate_commissions", lazy="select"
    )
    referred_user: Mapped["User"] = relationship(
        "User", foreign_keys=[referred_user_id], lazy="select"
    )
    order: Mapped["Order"] = relationship("Order", lazy="select")


class AffiliateClick(Base, CreatedAtMixin):
    """Bản ghi lượt click truy cập vào đường link giới thiệu."""
    __tablename__ = "affiliate_clicks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    affiliate_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    referral_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    affiliate_user: Mapped["User"] = relationship(
        "User", back_populates="affiliate_clicks", lazy="select"
    )
