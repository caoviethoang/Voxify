"""Model Voice dùng chung (Issue #18) — Thư viện giọng tập trung.

Thống nhất giọng hệ thống, giọng clone, giọng import về một bảng duy nhất.
"""
from typing import Optional

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, CreatedAtMixin, TimestampMixin


class Voice(Base, TimestampMixin):
    """Thư viện giọng đọc tập trung — dùng chung cho Studio, Voice Library và API."""
    __tablename__ = "voices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Chủ sở hữu (null = giọng hệ thống, có giá trị = giọng cá nhân)
    owner_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Thông tin hiển thị
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Nguồn gốc giọng
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # edge | azure | elevenlabs | user_clone
    provider_voice_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # ID gốc từ provider (edge-tts locale ID)

    # Phân loại
    voice_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="system", index=True
    )  # "system" | "cloned" | "imported"
    language: Mapped[str] = mapped_column(String(20), nullable=False, default="vi-VN", index=True)
    gender: Mapped[str] = mapped_column(String(20), nullable=False, default="Unknown")  # Female | Male | Unknown
    tags: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )  # Phong cách phân cách bằng dấu phẩy: "đọc truyện,tin tức,quảng cáo,podcast"

    # URL preview (không tốn credit)
    preview_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    sample_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Quyền truy cập
    visibility: Mapped[str] = mapped_column(
        String(20), nullable=False, default="private"
    )  # "private" | "public"

    # Trạng thái
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ready", index=True
    )  # "ready" | "processing" | "failed"
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # Pháp lý & bản quyền
    consent_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # FK tới voice_consent_logs.id
    license_note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Kinh tế
    tier: Mapped[str] = mapped_column(String(20), nullable=False, default="free")  # "free" | "premium"
    credit_multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # FK tới cloned_voices.voice_id nếu type="cloned"
    cloned_voice_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Thống kê
    total_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    owner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[owner_id])  # type: ignore[name-defined]  # noqa: F821
    favorites: Mapped[list["VoiceFavorite"]] = relationship(
        "VoiceFavorite", back_populates="voice", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_voices_provider_active", "provider", "is_active"),
        Index("ix_voices_type_lang", "voice_type", "language"),
    )


class VoiceFavorite(Base, CreatedAtMixin):
    """Danh sách yêu thích giọng đọc của từng người dùng."""
    __tablename__ = "voice_favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # voice_id tham chiếu tới voices.id HOẶC voice_id dạng string (giọng hệ thống từ edge-tts)
    voice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("voices.id", ondelete="CASCADE"), nullable=False, index=True
    )

    voice: Mapped["Voice"] = relationship("Voice", back_populates="favorites")

    __table_args__ = (
        UniqueConstraint("user_id", "voice_id", name="uq_voice_favorites_user_voice"),
    )
