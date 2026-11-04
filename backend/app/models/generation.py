"""Model lịch sử tạo audio."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Generation(Base):
    __tablename__ = "generations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # user_id nullable — cho phép anonymous user (Phase 1 chưa có auth)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    voice: Mapped[str] = mapped_column(String(100), nullable=False)
    rate: Mapped[str] = mapped_column(String(20), default="+0%", nullable=False)
    pitch: Mapped[str] = mapped_column(String(20), default="+0Hz", nullable=False)
    volume: Mapped[str] = mapped_column(String(20), default="+0%", nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # Đường dẫn file audio lưu trên storage
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # is_preview: True nếu chỉ tạo 200 ký tự đầu
    is_preview: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="edge", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    user: Mapped[Optional["User"]] = relationship("User", back_populates="generations")
