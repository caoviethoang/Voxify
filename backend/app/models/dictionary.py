"""Model từ điển phát âm cá nhân (Pronunciation Dictionary)."""
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class PronunciationDictionary(Base):
    __tablename__ = "pronunciation_dictionaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Từ gốc cần thay thế (ví dụ: "TP.HCM", "AI", "12/05/2026")
    word: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    # Cách đọc phiên âm / thay thế (ví dụ: "Thành phố Hồ Chí Minh", "Ây Ai")
    replacement: Mapped[str] = mapped_column(String(255), nullable=False)
    # Phân loại: "abbreviation" (viết tắt), "date", "number", "name", "custom"
    category: Mapped[str] = mapped_column(String(50), default="custom", nullable=False)
    # Trạng thái kích hoạt của quy tắc này
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="pronunciation_rules")
