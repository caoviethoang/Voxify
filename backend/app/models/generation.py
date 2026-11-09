"""Model lịch sử tạo audio và tiến độ job bất đồng bộ."""
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Generation(Base):
    __tablename__ = "generations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    voice: Mapped[str] = mapped_column(String(100), nullable=False)
    rate: Mapped[str] = mapped_column(String(20), default="+0%", nullable=False)
    pitch: Mapped[str] = mapped_column(String(20), default="+0Hz", nullable=False)
    volume: Mapped[str] = mapped_column(String(20), default="+0%", nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Đường dẫn file audio và phụ đề lưu trên storage
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    srt_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    vtt_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Định dạng âm thanh ("mp3" | "wav") và thời lượng audio (giây)
    format: Mapped[str] = mapped_column(String(10), default="mp3", nullable=False)
    duration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Trạng thái job bất đồng bộ ("queued" | "processing" | "done" | "failed")
    status: Mapped[str] = mapped_column(String(20), default="done", nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Credit tiêu hao
    credit_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # is_preview: True nếu chỉ tạo 200 ký tự đầu
    is_preview: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="edge", nullable=False)

    # Tiêu đề tùy chỉnh do người dùng đặt (tối đa 200 ký tự)
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Webhook callback URL khi hoàn thành job async (Issue #13)
    webhook_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

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

    user: Mapped[Optional["User"]] = relationship("User", back_populates="generations")
