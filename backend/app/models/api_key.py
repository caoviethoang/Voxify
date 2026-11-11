"""Models cho tính năng Quản lý API Key & Developers (Prompt 11 / Issue #13)."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, CreatedAtMixin


class ApiKey(Base, CreatedAtMixin):
    """
    Bản ghi lưu trữ API Key của người dùng.
    NGUYÊN TẮC BẢO MẬT:
    - Không bao giờ lưu trữ raw API key trong cơ sở dữ liệu.
    - Chỉ lưu trữ chuỗi băm mật mã SHA-256 (hashed_key).
    - key_prefix được lưu để hiển thị danh sách (ví dụ: vx_live_abc123...****).
    """
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    hashed_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="api_keys")
    usage_logs: Mapped[list["ApiUsageLog"]] = relationship(
        "ApiUsageLog", back_populates="api_key", cascade="all, delete-orphan"
    )


class ApiUsageLog(Base, CreatedAtMixin):
    """Lịch sử các yêu cầu gọi Public API v1 phục vụ thống kê & rate limiting."""
    __tablename__ = "api_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    credits_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    api_key: Mapped["ApiKey"] = relationship("ApiKey", back_populates="usage_logs")
    user: Mapped["User"] = relationship("User")
