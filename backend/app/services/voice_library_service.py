"""Service quản lý Thư viện Giọng tập trung (Voice Library) — Issue #18."""
import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, delete, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloned_voice import ClonedVoice
from app.models.voice import Voice, VoiceFavorite

logger = logging.getLogger(__name__)


class VoiceLibraryService:
    """Service điều phối toàn bộ Thư viện Giọng tập trung."""

    # -------------------------------------------------------------------------
    # Đồng bộ giọng hệ thống từ edge-tts/provider vào bảng voices
    # -------------------------------------------------------------------------

    @staticmethod
    async def sync_system_voices(
        db: AsyncSession,
        provider_voices: List[Dict[str, Any]],
        provider: str = "edge",
    ) -> int:
        """
        Đồng bộ danh sách giọng từ provider vào bảng voices.
        - Tạo mới nếu chưa tồn tại (dựa theo provider + provider_voice_id).
        - Cập nhật tên/ngôn ngữ/giới tính nếu đã có.
        - Trả về số lượng giọng được đồng bộ.
        """
        synced = 0
        now = datetime.now(UTC)

        # Lấy toàn bộ giọng system đang có trong DB
        result = await db.execute(
            select(Voice).where(
                and_(Voice.provider == provider, Voice.voice_type == "system")
            )
        )
        existing: Dict[str, Voice] = {v.provider_voice_id or "": v for v in result.scalars().all()}

        for pv in provider_voices:
            pvid: str = pv.get("id", "")
            if not pvid:
                continue

            if pvid in existing:
                # Cập nhật thông tin
                v = existing[pvid]
                v.name = pv.get("name", v.name)
                v.language = pv.get("locale", v.language)
                v.gender = pv.get("gender", v.gender)
                v.updated_at = now
            else:
                # Tạo mới
                new_voice = Voice(
                    owner_id=None,
                    name=pv.get("name", pvid),
                    display_name=pv.get("full_name") or pv.get("name", pvid),
                    provider=provider,
                    provider_voice_id=pvid,
                    voice_type="system",
                    language=pv.get("locale", "unknown"),
                    gender=pv.get("gender", "Unknown"),
                    visibility="public",
                    status="ready",
                    is_active=True,
                    tier=pv.get("tier", "free"),
                    credit_multiplier=float(pv.get("credit_multiplier", 1.0)),
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_voice)
            synced += 1

        await db.commit()
        logger.info(f"Đồng bộ {synced} giọng {provider} vào bảng voices")
        return synced

    @staticmethod
    async def sync_cloned_voice_to_library(
        db: AsyncSession,
        cloned: ClonedVoice,
    ) -> Voice:
        """
        Đồng bộ / cập nhật một ClonedVoice vào bảng voices (voice_type=cloned).
        """
        result = await db.execute(
            select(Voice).where(
                and_(
                    Voice.cloned_voice_ref == cloned.voice_id,
                    Voice.voice_type == "cloned",
                )
            )
        )
        existing_voice = result.scalar_one_or_none()
        now = datetime.now(UTC)

        if existing_voice:
            existing_voice.name = cloned.name
            existing_voice.description = cloned.description
            existing_voice.language = cloned.language
            existing_voice.gender = cloned.gender
            existing_voice.status = cloned.status
            existing_voice.is_active = cloned.is_active
            existing_voice.preview_url = cloned.preview_audio_url
            existing_voice.sample_duration = cloned.sample_duration
            existing_voice.updated_at = now
            await db.commit()
            await db.refresh(existing_voice)
            return existing_voice

        new_voice = Voice(
            owner_id=cloned.user_id,
            name=cloned.name,
            display_name=cloned.name,
            description=cloned.description,
            provider="user_clone",
            provider_voice_id=cloned.voice_id,
            voice_type="cloned",
            language=cloned.language,
            gender=cloned.gender,
            preview_url=cloned.preview_audio_url,
            sample_duration=cloned.sample_duration,
            visibility="private",
            status=cloned.status,
            is_active=cloned.is_active,
            cloned_voice_ref=cloned.voice_id,
            tier="free",
            credit_multiplier=float(cloned.quality_score or 1.0),
            created_at=now,
            updated_at=now,
        )
        db.add(new_voice)
        await db.commit()
        await db.refresh(new_voice)
        return new_voice

    # -------------------------------------------------------------------------
    # Truy vấn danh sách giọng
    # -------------------------------------------------------------------------

    @staticmethod
    async def list_voices(
        db: AsyncSession,
        user_id: Optional[int] = None,
        voice_type: Optional[str] = None,
        language: Optional[str] = None,
        gender: Optional[str] = None,
        search: Optional[str] = None,
        only_active: bool = True,
        favorites_only: bool = False,
        owner_only: bool = False,
        limit: int = 500,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Lấy danh sách giọng từ bảng voices với bộ lọc đa chiều.
        """
        conditions: List[Any] = []

        if only_active:
            conditions.append(Voice.is_active.is_(True))
            conditions.append(Voice.status == "ready")

        if owner_only and user_id:
            conditions.append(Voice.owner_id == user_id)
        elif voice_type:
            # Lọc theo loại (system / cloned)
            conditions.append(Voice.voice_type == voice_type)
        else:
            # Mặc định: system (public) + cloned của user hiện tại
            if user_id:
                from sqlalchemy import or_
                conditions.append(
                    or_(
                        Voice.visibility == "public",
                        and_(Voice.owner_id == user_id, Voice.visibility == "private"),
                    )
                )
            else:
                conditions.append(Voice.visibility == "public")

        # Lọc ngôn ngữ
        if language and language != "all":
            if language == "vi":
                conditions.append(Voice.language.startswith("vi"))
            else:
                conditions.append(Voice.language == language)

        # Lọc giới tính
        if gender and gender not in ("all", ""):
            conditions.append(Voice.gender == gender)

        # Tìm kiếm theo tên
        if search:
            conditions.append(Voice.name.ilike(f"%{search}%"))

        # Tab yêu thích
        if favorites_only and user_id:
            fav_subq = select(VoiceFavorite.voice_id).where(VoiceFavorite.user_id == user_id).scalar_subquery()
            conditions.append(Voice.id.in_(fav_subq))

        # Truy vấn chính
        where_clause = and_(*conditions) if conditions else true()

        # Đếm tổng
        count_result = await db.execute(select(func.count()).select_from(Voice).where(where_clause))
        total = count_result.scalar_one()

        # Lấy dữ liệu
        query = (
            select(Voice)
            .where(where_clause)
            .order_by(
                Voice.voice_type,       # system trước, cloned sau
                Voice.language,         # vi-VN ưu tiên
                Voice.name,
            )
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        voices = list(result.scalars().all())

        # Lấy danh sách yêu thích của user
        fav_ids: set[int] = set()
        if user_id:
            fav_result = await db.execute(
                select(VoiceFavorite.voice_id).where(VoiceFavorite.user_id == user_id)
            )
            fav_ids = {r[0] for r in fav_result.all()}

        return {
            "total": total,
            "voices": voices,
            "favorite_ids": list(fav_ids),
        }

    # -------------------------------------------------------------------------
    # Yêu thích
    # -------------------------------------------------------------------------

    @staticmethod
    async def toggle_favorite(
        db: AsyncSession,
        user_id: int,
        voice_id: int,
    ) -> bool:
        """
        Thêm/xoá yêu thích giọng đọc. Trả về True nếu đã thêm, False nếu đã xoá.
        """
        result = await db.execute(
            select(VoiceFavorite).where(
                and_(VoiceFavorite.user_id == user_id, VoiceFavorite.voice_id == voice_id)
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            await db.delete(existing)
            await db.commit()
            return False
        else:
            fav = VoiceFavorite(
                user_id=user_id,
                voice_id=voice_id,
                created_at=datetime.now(UTC),
            )
            db.add(fav)
            await db.commit()
            return True

    @staticmethod
    async def get_favorites(db: AsyncSession, user_id: int) -> List[int]:
        """Trả về danh sách voice_id mà user đã yêu thích."""
        result = await db.execute(
            select(VoiceFavorite.voice_id).where(VoiceFavorite.user_id == user_id)
        )
        return [r[0] for r in result.all()]

    # -------------------------------------------------------------------------
    # Thống kê / Admin
    # -------------------------------------------------------------------------

    @staticmethod
    async def set_voice_active(
        db: AsyncSession,
        voice_id: int,
        is_active: bool,
    ) -> Optional[Voice]:
        """Admin: bật / tắt giọng đọc trong thư viện."""
        result = await db.execute(select(Voice).where(Voice.id == voice_id))
        voice = result.scalar_one_or_none()
        if not voice:
            return None
        voice.is_active = is_active
        voice.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(voice)
        return voice

    @staticmethod
    async def remove_user_cloned_voices(db: AsyncSession, cloned_voice_ref: str) -> None:
        """Xoá voice record khỏi thư viện khi cloned voice bị xoá."""
        await db.execute(
            delete(Voice).where(
                and_(
                    Voice.cloned_voice_ref == cloned_voice_ref,
                    Voice.voice_type == "cloned",
                )
            )
        )
        await db.commit()

    @staticmethod
    async def get_voice_by_id(db: AsyncSession, voice_id: int) -> Optional[Voice]:
        """Lấy chi tiết một giọng theo ID."""
        result = await db.execute(select(Voice).where(Voice.id == voice_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_voice_by_provider_id(
        db: AsyncSession, provider: str, provider_voice_id: str
    ) -> Optional[Voice]:
        """Lấy giọng theo provider + provider_voice_id (edge-tts locale)."""
        result = await db.execute(
            select(Voice).where(
                and_(
                    Voice.provider == provider,
                    Voice.provider_voice_id == provider_voice_id,
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def increment_voice_usage(db: AsyncSession, voice_provider_id: str) -> None:
        """Tăng bộ đếm total_uses khi giọng được sử dụng để tổng hợp audio."""
        result = await db.execute(
            select(Voice).where(Voice.provider_voice_id == voice_provider_id)
        )
        voice = result.scalar_one_or_none()
        if voice:
            voice.total_uses += 1
            await db.commit()
