"""Dịch vụ quản lý Credit — Nguồn sự thật duy nhất (Single Source of Truth) về credit."""
import asyncio
from math import ceil
from typing import Dict, List, Optional, Tuple

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.errors import AppError
from app.models.credit import CreditTransaction, CreditTransactionType
from app.models.user import User


class InsufficientCreditsError(AppError):
    """Lỗi khi số dư credit không đủ."""
    def __init__(self, required: int, current: int):
        super().__init__(
            code="INSUFFICIENT_CREDITS",
            message=f"Số dư credit không đủ để thực hiện yêu cầu. Cần {required:,} credit, hiện có {current:,} credit.",
            status_code=402,
        )
        self.required = required
        self.current = current


class CreditService:
    """Service Object quản lý số dư và sổ cái credit."""

    # Khóa đồng bộ trong bộ nhớ cho môi trường SQLite để tránh 'database is locked' khi concurrency cao
    _user_locks: Dict[int, asyncio.Lock] = {}
    _global_lock = asyncio.Lock()

    @classmethod
    async def _get_user_lock(cls, user_id: int) -> asyncio.Lock:
        async with cls._global_lock:
            if user_id not in cls._user_locks:
                cls._user_locks[user_id] = asyncio.Lock()
            return cls._user_locks[user_id]

    @staticmethod
    def calculate_cost(char_count: int, provider: str = "edge", voice: str = "") -> int:
        """
        Quy tắc tính credit:
        1 ký tự = 1 credit (từ config).
        Hệ số nhân theo provider (edge: 1.0, azure: 1.2, elevenlabs: 2.0).
        """
        settings = get_settings()
        if char_count <= 0:
            return 0

        multipliers = settings.credit_provider_multipliers or {}
        multiplier = multipliers.get(provider.lower(), 1.0)
        chars_per_credit = max(1, settings.credit_chars_per_credit)

        cost = ceil((char_count * multiplier) / chars_per_credit)
        return max(1, cost)

    @classmethod
    async def reserve(
        cls,
        db: AsyncSession,
        user_id: int,
        amount: int,
        ref_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> CreditTransaction:
        """
        Khấu trừ credit trước khi thực thi job (Reserve pattern).
        Khóa hàng (Row lock) để chống race condition.
        """
        if amount < 0:
            raise ValueError("Số lượng credit cần trừ phải là số dương")
        if amount == 0:
            # Miễn phí (ví dụ nghe thử)
            user = await cls._get_user_for_update(db, user_id)
            if not user:
                raise AppError(code="NOT_FOUND", message="Không tìm thấy người dùng", status_code=404)
            return CreditTransaction(
                user_id=user_id,
                amount=0,
                type=CreditTransactionType.USAGE.value,
                ref_id=ref_id,
                balance_after=user.credit_balance,
                description=description or "Nghe thử miễn phí",
            )

        lock = await cls._get_user_lock(user_id)
        async with lock:
            user = await cls._get_user_for_update(db, user_id)
            if not user:
                raise AppError(code="NOT_FOUND", message="Không tìm thấy người dùng", status_code=404)

            current_balance = user.credit_balance
            if current_balance < amount:
                raise InsufficientCreditsError(required=amount, current=current_balance)

            new_balance = current_balance - amount
            user.credit_balance = new_balance
            user.credits = new_balance

            tx = CreditTransaction(
                user_id=user_id,
                amount=-amount,
                type=CreditTransactionType.USAGE.value,
                ref_id=ref_id,
                balance_after=new_balance,
                description=description or f"Sử dụng dịch vụ TTS ({amount} credit)",
            )
            db.add(tx)
            await db.commit()
            return tx

    @classmethod
    async def refund(
        cls,
        db: AsyncSession,
        user_id: int,
        amount: int,
        ref_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> CreditTransaction:
        """
        Hoàn lại credit nếu job lỗi (Refund pattern).
        """
        if amount <= 0:
            raise ValueError("Số lượng hoàn tiền phải lớn hơn 0")

        lock = await cls._get_user_lock(user_id)
        async with lock:
            user = await cls._get_user_for_update(db, user_id)
            if not user:
                raise AppError(code="NOT_FOUND", message="Không tìm thấy người dùng", status_code=404)

            new_balance = user.credit_balance + amount
            user.credit_balance = new_balance
            user.credits = new_balance

            tx = CreditTransaction(
                user_id=user_id,
                amount=amount,
                type=CreditTransactionType.REFUND.value,
                ref_id=ref_id,
                balance_after=new_balance,
                description=reason or f"Hoàn lại credit do lỗi xử lý ({amount} credit)",
            )
            db.add(tx)
            await db.commit()
            return tx

    @classmethod
    async def add_signup_bonus(cls, db: AsyncSession, user_id: int) -> CreditTransaction:
        """
        Tặng credit khi đăng ký tài khoản mới (config, mặc định 10.000).
        """
        settings = get_settings()
        bonus_amount = settings.credit_signup_bonus

        lock = await cls._get_user_lock(user_id)
        async with lock:
            user = await cls._get_user_for_update(db, user_id)
            if not user:
                raise AppError(code="NOT_FOUND", message="Không tìm thấy người dùng", status_code=404)

            new_balance = user.credit_balance + bonus_amount
            user.credit_balance = new_balance
            user.credits = new_balance

            tx = CreditTransaction(
                user_id=user_id,
                amount=bonus_amount,
                type=CreditTransactionType.SIGNUP_BONUS.value,
                ref_id="signup_bonus",
                balance_after=new_balance,
                description="Tặng thưởng chào mừng thành viên mới",
            )
            db.add(tx)
            await db.commit()
            return tx

    @classmethod
    async def add_adjustment(
        cls,
        db: AsyncSession,
        user_id: int,
        amount: int,
        tx_type: str = CreditTransactionType.ADMIN_ADJUST.value,
        ref_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> CreditTransaction:
        """
        Điều chỉnh credit (Admin adjust, nạp tiền purchase, hoa hồng affiliate...).
        """
        lock = await cls._get_user_lock(user_id)
        async with lock:
            user = await cls._get_user_for_update(db, user_id)
            if not user:
                raise AppError(code="NOT_FOUND", message="Không tìm thấy người dùng", status_code=404)

            if user.credit_balance + amount < 0:
                raise InsufficientCreditsError(required=abs(amount), current=user.credit_balance)

            new_balance = user.credit_balance + amount
            user.credit_balance = new_balance
            user.credits = new_balance

            tx = CreditTransaction(
                user_id=user_id,
                amount=amount,
                type=tx_type,
                ref_id=ref_id,
                balance_after=new_balance,
                description=description,
            )
            db.add(tx)
            await db.commit()
            return tx

    @classmethod
    async def get_balance(cls, db: AsyncSession, user_id: int) -> int:
        """Lấy số dư credit hiện tại của user."""
        stmt = select(User.credit_balance).where(User.id == user_id)
        res = await db.execute(stmt)
        val = res.scalar_one_or_none()
        return val if val is not None else 0

    @classmethod
    async def verify_ledger(cls, db: AsyncSession, user_id: int) -> Tuple[int, int, bool]:
        """
        Đối soát số dư: Tổng ledger sum(amount) vs cache users.credit_balance.
        Trả về: (ledger_sum, cached_balance, is_matching)
        """
        stmt_sum = select(func.coalesce(func.sum(CreditTransaction.amount), 0)).where(
            CreditTransaction.user_id == user_id
        )
        res_sum = await db.execute(stmt_sum)
        ledger_sum = int(res_sum.scalar() or 0)

        cached_balance = await cls.get_balance(db, user_id)
        return (ledger_sum, cached_balance, ledger_sum == cached_balance)

    @classmethod
    async def list_transactions(
        cls,
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        limit: int = 20,
        tx_type: Optional[str] = None,
    ) -> Tuple[List[CreditTransaction], int]:
        """
        Lấy danh sách lịch sử biến động credit dạng sổ cái, có phân trang và lọc theo type.
        """
        page = max(1, page)
        limit = max(1, min(limit, 100))
        offset = (page - 1) * limit

        base_query = select(CreditTransaction).where(CreditTransaction.user_id == user_id)
        count_query = select(func.count(CreditTransaction.id)).where(CreditTransaction.user_id == user_id)

        if tx_type:
            base_query = base_query.where((CreditTransaction.type == tx_type) | (CreditTransaction.tx_type == tx_type))
            count_query = count_query.where((CreditTransaction.type == tx_type) | (CreditTransaction.tx_type == tx_type))

        # Đếm tổng số
        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        # Lấy dữ liệu theo trang
        stmt = base_query.order_by(desc(CreditTransaction.created_at)).offset(offset).limit(limit)
        res = await db.execute(stmt)
        items = list(res.scalars().all())

        return items, total

    @staticmethod
    async def _get_user_for_update(db: AsyncSession, user_id: int) -> Optional[User]:
        """Lấy user với khóa row-level lock (FOR UPDATE)."""
        stmt = select(User).where(User.id == user_id).with_for_update()
        res = await db.execute(stmt)
        return res.scalar_one_or_none()
