"""Models cho hệ thống Thanh toán, Gói dịch vụ, Mã giảm giá và Đơn hàng."""
import enum
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class PlanType(str, enum.Enum):
    CREDIT_PACK = "credit_pack"
    SUBSCRIPTION = "subscription"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    VIETQR = "vietqr"
    PAYOS = "payos"
    STRIPE = "stripe"


class DiscountType(str, enum.Enum):
    PERCENT = "percent"
    FIXED = "fixed"


class PricingPlan(Base):
    """Cấu hình các gói dịch vụ và gói nạp credit lưu trong DB."""
    __tablename__ = "pricing_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False, default=PlanType.CREDIT_PACK.value)
    price: Mapped[int] = mapped_column(Integer, nullable=False)  # VND
    currency: Mapped[str] = mapped_column(String(10), default="VND", nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)  # Số lượng credit cộng vào tài khoản
    duration_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0 cho gói lượt, 30 cho gói tháng
    storage_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)  # Thời gian lưu trữ file
    has_premium_voices: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_api_access: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    queue_priority: Mapped[str] = mapped_column(String(20), default="standard", nullable=False)  # standard | high | ultra
    concurrency_limit: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    badge: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # ví dụ: "Phổ biến", "Tiết kiệm 20%"
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="plan")


class Coupon(Base):
    """Mã giảm giá."""
    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    discount_type: Mapped[str] = mapped_column(String(20), default=DiscountType.PERCENT.value, nullable=False)  # percent | fixed
    discount_value: Mapped[int] = mapped_column(Integer, nullable=False)  # % hoặc số tiền VND
    min_order_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_uses: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="coupon")


class Order(Base):
    """Quản lý đơn hàng nạp credit / nâng cấp gói."""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    order_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)  # Số nguyên cho PayOS orderCode
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("pricing_plans.id", ondelete="SET NULL"), nullable=True
    )
    coupon_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("coupons.id", ondelete="SET NULL"), nullable=True
    )

    original_amount: Mapped[int] = mapped_column(Integer, nullable=False)  # VND
    discount_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    final_amount: Mapped[int] = mapped_column(Integer, nullable=False)  # VND
    credits_to_add: Mapped[int] = mapped_column(Integer, nullable=False)

    payment_method: Mapped[str] = mapped_column(String(20), default=PaymentMethod.VIETQR.value, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=OrderStatus.PENDING.value, nullable=False, index=True)

    # Dữ liệu thanh toán & QR Code
    qr_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    checkout_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    transfer_content: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    bank_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bank_account_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bank_account_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    payment_transaction_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="orders", lazy="selectin")
    plan: Mapped[Optional["PricingPlan"]] = relationship("PricingPlan", back_populates="orders", lazy="selectin")
    coupon: Mapped[Optional["Coupon"]] = relationship("Coupon", back_populates="orders", lazy="selectin")


class PaymentWebhookLog(Base):
    """Sổ nhật ký webhook thanh toán để đảm bảo Idempotent tuyệt đối."""
    __tablename__ = "payment_webhook_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    gateway: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    order_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
