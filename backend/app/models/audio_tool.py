"""Model lưu trữ tiến trình & lịch sử các tác vụ công cụ âm thanh (AudioToolJob)."""
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class AudioToolJob(Base):
    """Bảng lưu trữ công việc xử lý của công cụ âm thanh (Audio Tools Framework)."""
    __tablename__ = "audio_tool_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Khóa ngoại người dùng
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ID của công cụ (ví dụ: trim, volume_normalize, format_converter...)
    tool_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Trạng thái công việc: queued | processing | done | failed
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued", index=True
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Tệp đầu vào
    input_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    input_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    input_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Tham số cấu hình dạng JSON string
    params: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Tệp kết quả đầu ra
    output_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    output_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    output_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    output_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Kinh tế & chi phí
    credit_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Quan hệ
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id])  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_audio_tool_jobs_user_status", "user_id", "status"),
        Index("ix_audio_tool_jobs_tool_status", "tool_id", "status"),
    )
