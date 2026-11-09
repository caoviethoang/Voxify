"""Model người dùng."""
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
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

    # Cache cột users.credit_balance cập nhật trong cùng transaction DB (sổ cái ledger)
    credit_balance: Mapped[int] = mapped_column(Integer, default=10000, nullable=False)
    # Giữ cột credits để tương thích ngược với code cũ / migration cũ
    credits: Mapped[int] = mapped_column(Integer, default=10000, nullable=False)

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
