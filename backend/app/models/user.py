"""Model người dùng."""
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)  # "user" | "admin"
    subscription_tier: Mapped[str] = mapped_column(String(50), default="free", nullable=False)  # "free" | "pro" | "vip"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    google_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, index=True)

    # Xác thực 2 bước (2FA / TOTP) & An ninh kiểm duyệt (Issue #16)
    two_factor_secret: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    violation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ban_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Tiếp thị liên kết & Chống gian lận (Affiliate & Anti-fraud - Issue #14)
    referral_code: Mapped[Optional[str]] = mapped_column(String(32), unique=True, nullable=True, index=True)
    referred_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    registration_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Cache cột users.credit_balance cập nhật trong cùng transaction DB (sổ cái ledger)
    credit_balance: Mapped[int] = mapped_column(Integer, default=10000, nullable=False)
    # Giữ cột credits để tương thích ngược với code cũ / migration cũ
    credits: Mapped[int] = mapped_column(Integer, default=10000, nullable=False)

    generations: Mapped[list["Generation"]] = relationship(
        "Generation", back_populates="user", lazy="select"
    )
    credit_transactions: Mapped[list["CreditTransaction"]] = relationship(
        "CreditTransaction", back_populates="user", lazy="select", cascade="all, delete-orphan"
    )
    pronunciation_rules: Mapped[list["PronunciationDictionary"]] = relationship(
        "PronunciationDictionary", back_populates="user", lazy="select", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )
    orders: Mapped[list["Order"]] = relationship(
        "Order", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )
    cloned_voices: Mapped[list["ClonedVoice"]] = relationship(
        "ClonedVoice", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )
    api_keys: Mapped[list["ApiKey"]] = relationship(
        "ApiKey", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )

    # Relationships cho Affiliate (Issue #14)
    referrer: Mapped[Optional["User"]] = relationship(
        "User", remote_side="User.id", back_populates="referrals", lazy="select"
    )
    referrals: Mapped[list["User"]] = relationship(
        "User", back_populates="referrer", lazy="select"
    )
    affiliate_clicks: Mapped[list["AffiliateClick"]] = relationship(
        "AffiliateClick", back_populates="affiliate_user", cascade="all, delete-orphan", lazy="select"
    )
    affiliate_commissions: Mapped[list["AffiliateCommission"]] = relationship(
        "AffiliateCommission",
        foreign_keys="[AffiliateCommission.affiliate_user_id]",
        back_populates="affiliate_user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    affiliate_withdrawals: Mapped[list["AffiliateWithdrawal"]] = relationship(
        "AffiliateWithdrawal",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
