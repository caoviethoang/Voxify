"""Model giao dịch credit (Sổ cái - Ledger)."""
import enum
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class CreditTransactionType(str, enum.Enum):
    SIGNUP_BONUS = "signup_bonus"
    PURCHASE = "purchase"
    USAGE = "usage"
    REFUND = "refund"
    ADMIN_ADJUST = "admin_adjust"
    AFFILIATE = "affiliate"
    VOICE_CLONE = "voice_clone"


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Số dương: nạp/cộng credit. Số âm: trừ credit.
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    # Giữ tx_type cho database schema ban đầu
    tx_type: Mapped[str] = mapped_column(String(30), nullable=False, default="usage")
    # Cột type theo chuẩn Prompt 4
    type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, default="usage")
    # Mã tham chiếu liên kết (job_id, generation_id, order_id, referral_id...)
    ref_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    # Số dư sau giao dịch (để kiểm tra chuỗi sổ cái không bị sai lệch)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="credit_transactions")

    def __init__(self, **kwargs):
        val = kwargs.get("type") or kwargs.get("tx_type") or "usage"
        kwargs["type"] = val
        kwargs["tx_type"] = val
        super().__init__(**kwargs)
