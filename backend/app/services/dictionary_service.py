"""Service quản lý từ điển phát âm cá nhân và thay thế từ trước khi đọc."""
import logging
import re
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dictionary import PronunciationDictionary

logger = logging.getLogger(__name__)


class DictionaryService:
    @staticmethod
    async def list_rules(db: AsyncSession, user_id: int) -> List[PronunciationDictionary]:
        """Lấy danh sách các quy tắc phát âm của người dùng."""
        stmt = (
            select(PronunciationDictionary)
            .where(PronunciationDictionary.user_id == user_id)
            .order_by(PronunciationDictionary.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def create_rule(
        db: AsyncSession,
        user_id: int,
        word: str,
        replacement: str,
        category: str = "custom",
    ) -> PronunciationDictionary:
        """Thêm từ phát âm mới vào từ điển cá nhân."""
        word_clean = word.strip()
        replacement_clean = replacement.strip()
        if not word_clean:
            raise ValueError("Từ gốc không được để trống")
        if not replacement_clean:
            raise ValueError("Cách đọc thay thế không được để trống")

        rule = PronunciationDictionary(
            user_id=user_id,
            word=word_clean,
            replacement=replacement_clean,
            category=category,
            is_active=True,
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        return rule

    @staticmethod
    async def delete_rule(db: AsyncSession, user_id: int, rule_id: int) -> bool:
        """Xóa quy tắc phát âm."""
        stmt = select(PronunciationDictionary).where(
            PronunciationDictionary.id == rule_id,
            PronunciationDictionary.user_id == user_id,
        )
        res = await db.execute(stmt)
        rule = res.scalar_one_or_none()
        if not rule:
            return False
        await db.delete(rule)
        await db.commit()
        return True

    @staticmethod
    async def toggle_rule(db: AsyncSession, user_id: int, rule_id: int, is_active: bool) -> Optional[PronunciationDictionary]:
        """Bật / tắt một quy tắc phát âm."""
        stmt = select(PronunciationDictionary).where(
            PronunciationDictionary.id == rule_id,
            PronunciationDictionary.user_id == user_id,
        )
        res = await db.execute(stmt)
        rule = res.scalar_one_or_none()
        if not rule:
            return None
        rule.is_active = is_active
        await db.commit()
        await db.refresh(rule)
        return rule

    @classmethod
    async def apply_dictionary(cls, db: AsyncSession, user_id: Optional[int], text: str) -> str:
        """
        Áp dụng các quy tắc từ điển phát âm đang kích hoạt của user lên văn bản.
        Ưu tiên các từ dài trước để tránh xung đột từ con.
        """
        if not user_id or not text:
            return text

        stmt = select(PronunciationDictionary).where(
            PronunciationDictionary.user_id == user_id,
            PronunciationDictionary.is_active == True,
        )
        res = await db.execute(stmt)
        rules = list(res.scalars().all())
        if not rules:
            return text

        # Sắp xếp từ dài nhất trước
        rules.sort(key=lambda r: len(r.word), reverse=True)

        result_text = text
        for r in rules:
            target = r.word.strip()
            repl = r.replacement.strip()
            if not target or not repl:
                continue

            # Sử dụng regex an toàn cho từ viết tắt/kí tự đặc biệt
            escaped_target = re.escape(target)
            # Khớp ranh giới từ nếu từ là chữ cái/số bình thường
            if re.match(r"^\w+$", target):
                pattern = rf"\b{escaped_target}\b"
            else:
                pattern = escaped_target

            result_text = re.sub(pattern, repl, result_text, flags=re.IGNORECASE)

        return result_text
