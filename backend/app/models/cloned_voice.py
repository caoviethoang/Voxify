"""Models cho tính năng Clone giọng nói (Voice Cloning), lưu audit log đồng ý và báo cáo lạm dụng."""
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ClonedVoice(Base):
    """Bản ghi giọng clone của người dùng."""
    __tablename__ = "cloned_voices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    voice_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # File mẫu âm thanh gốc (5 giây – 3 phút)
    audio_sample_path: Mapped[str] = mapped_column(String(500), nullable=False)
    sample_duration: Mapped[float] = mapped_column(Float, nullable=False)
    sample_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Thang điểm 1.0 - 5.0

    # Thông tin ngôn ngữ & giới tính
    gender: Mapped[str] = mapped_column(String(20), default="unspecified", nullable=False)
    language: Mapped[str] = mapped_column(String(20), default="vi-VN", nullable=False)

    # Provider thông tin
    provider: Mapped[str] = mapped_column(String(50), default="mock", nullable=False)
    provider_voice_id: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    # Mẫu phát thử âm thanh
    preview_audio_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    preview_audio_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Trạng thái: "ready" | "processing" | "failed" | "reported" | "deleted"
    status: Mapped[str] = mapped_column(String(30), default="ready", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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

    user: Mapped["User"] = relationship("User", back_populates="cloned_voices")
    consent_logs: Mapped[list["VoiceConsentLog"]] = relationship(
        "VoiceConsentLog", back_populates="cloned_voice", cascade="all, delete-orphan"
    )
    abuse_reports: Mapped[list["VoiceAbuseReport"]] = relationship(
        "VoiceAbuseReport", back_populates="cloned_voice", cascade="all, delete-orphan"
    )


class VoiceConsentLog(Base):
    """Audit log đồng ý bản quyền & cam kết chủ quyền giọng nói (Bắt buộc theo luật/quy định)."""
    __tablename__ = "voice_consent_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cloned_voice_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("cloned_voices.id", ondelete="CASCADE"), nullable=True, index=True
    )
    voice_name: Mapped[str] = mapped_column(String(100), nullable=False)
    audio_sample_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    consent_text: Mapped[str] = mapped_column(Text, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User")
    cloned_voice: Mapped[Optional["ClonedVoice"]] = relationship("ClonedVoice", back_populates="consent_logs")


class VoiceAbuseReport(Base):
    """Báo cáo vi phạm / lạm dụng clone giọng nói (mạo danh, không có sự đồng ý, phỉ báng)."""
    __tablename__ = "voice_abuse_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cloned_voice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cloned_voices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reporter_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reporter_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reason: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "celebrity_impersonation" | "no_consent" | "copyright" | "defamation" | "other"
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)  # pending | reviewed | resolved | dismissed
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    cloned_voice: Mapped["ClonedVoice"] = relationship("ClonedVoice", back_populates="abuse_reports")
    reporter_user: Mapped[Optional["User"]] = relationship("User")
