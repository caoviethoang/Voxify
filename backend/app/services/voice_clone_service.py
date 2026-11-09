"""Dịch vụ nghiệp vụ cho tính năng Clone giọng nói (VoiceCloneService)."""
import logging
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.errors import AppError
from app.core.voice_anti_abuse import (
    VALID_ABUSE_REASONS,
    check_voice_name_against_blocklist,
)
from app.models.cloned_voice import ClonedVoice, VoiceAbuseReport, VoiceConsentLog
from app.models.payment import Order, PricingPlan
from app.models.user import User
from app.providers.clone_base import CloneProvider
from app.providers.clone_factory import get_clone_provider
from app.schemas.voice_clone import VoiceCloneQuota
from app.services.audio_service import AudioService
from app.services.credit_service import CreditService, InsufficientCreditsError

logger = logging.getLogger(__name__)

CONSENT_MANDATORY_STATEMENT = (
    "Đây là giọng của tôi hoặc tôi có sự đồng ý bằng văn bản của chủ giọng. "
    "Tôi cam kết chịu hoàn toàn trách nhiệm pháp lý đối với nội dung phát sinh và không sử dụng nhằm mục đích lừa đảo, giả mạo hay vi phạm pháp luật."
)


class VoiceCloneService:
    def __init__(self, provider: Optional[CloneProvider] = None):
        self.provider = provider or get_clone_provider()

    @staticmethod
    async def get_user_quota(db: AsyncSession, user: User) -> VoiceCloneQuota:
        """Kiểm tra hạn mức tạo giọng clone theo gói cước."""
        settings = get_settings()

        # Đếm số giọng clone đang hoạt động
        stmt = (
            select(func.count(ClonedVoice.id))
            .where(ClonedVoice.user_id == user.id)
            .where(ClonedVoice.is_active.is_(True))
        )
        res = await db.execute(stmt)
        used = res.scalar() or 0

        # Nếu là admin: không giới hạn
        if user.is_admin or user.role == "admin":
            return VoiceCloneQuota(
                used=used,
                max_allowed=100,
                plan_name="Admin (Không giới hạn)",
                creation_fee=0,
                multiplier=getattr(settings, "clone_voice_multiplier", 1.5),
            )

        # Kiểm tra gói subscription đang hoạt động của người dùng
        plan_stmt = (
            select(PricingPlan)
            .join(Order, Order.plan_id == PricingPlan.id)
            .where(Order.user_id == user.id)
            .where(Order.status == "paid")
            .where(PricingPlan.type == "subscription")
            .order_by(PricingPlan.price.desc())
            .limit(1)
        )
        plan_res = await db.execute(plan_stmt)
        active_plan = plan_res.scalar_one_or_none()

        if active_plan:
            code = active_plan.code.lower()
            if "business" in code or "vip" in code:
                max_allowed = getattr(settings, "max_cloned_voices_vip", 20)
                plan_name = active_plan.name
            elif "pro" in code:
                max_allowed = getattr(settings, "max_cloned_voices_pro", 5)
                plan_name = active_plan.name
            else:
                max_allowed = getattr(settings, "max_cloned_voices_free", 1)
                plan_name = active_plan.name
        else:
            max_allowed = getattr(settings, "max_cloned_voices_free", 1)
            plan_name = "Gói Miễn Phí"

        return VoiceCloneQuota(
            used=used,
            max_allowed=max_allowed,
            plan_name=plan_name,
            creation_fee=getattr(settings, "clone_creation_fee", 500),
            multiplier=getattr(settings, "clone_voice_multiplier", 1.5),
        )

    async def create_cloned_voice(
        self,
        db: AsyncSession,
        user: User,
        name: str,
        description: Optional[str],
        file_bytes: bytes,
        filename: str,
        consent_accepted: bool,
        gender: str = "unspecified",
        language: str = "vi-VN",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ClonedVoice:
        """
        Quy trình tạo giọng clone hoàn chỉnh:
        1. Kiểm tra điều khoản đồng ý (BẮT BUỘC)
        2. Chặn clone người nổi tiếng / chính trị gia
        3. Kiểm tra hạn mức theo gói
        4. Kiểm tra số dư credit
        5. Lưu file & kiểm tra chất lượng âm thanh (5–30s, độ ồn)
        6. Đăng ký với CloneProvider
        7. Khấu trừ credit 1 lần (500 credits)
        8. Lưu audit log đồng ý
        9. Sinh mẫu phát thử preview
        10. Lưu bản ghi ClonedVoice
        """
        settings = get_settings()
        clean_name = name.strip()
        if not clean_name:
            raise AppError("INVALID_NAME", "Vui lòng nhập tên cho giọng đọc clone.", 400)

        # 1. Bảo vệ bản quyền & Chống lạm dụng (BẮT BUỘC)
        if not consent_accepted:
            raise AppError(
                "CONSENT_REQUIRED",
                "Bạn bắt buộc phải xác nhận cam kết: 'Đây là giọng của tôi hoặc tôi có sự đồng ý bằng văn bản của chủ giọng' để tiếp tục.",
                400,
            )

        # 2. Chặn clone giọng người nổi tiếng / chính trị gia
        is_blocked, detected, block_reason = check_voice_name_against_blocklist(clean_name, description)
        if is_blocked and block_reason:
            logger.warning(f"Chặn clone giọng người nổi tiếng: user={user.id}, name='{clean_name}', detected='{detected}'")
            raise AppError("CELEBRITY_VOICE_BLOCKED", block_reason, 400)

        # 3. Kiểm tra hạn mức theo gói cước
        quota = await self.get_user_quota(db, user)
        if quota.used >= quota.max_allowed:
            raise AppError(
                "QUOTA_EXCEEDED",
                f"Bạn đã sử dụng hết hạn mức ({quota.used}/{quota.max_allowed} giọng) của {quota.plan_name}. "
                "Vui lòng nâng cấp gói cước để tạo thêm giọng clone.",
                403,
            )

        # 4. Kiểm tra credit phí tạo giọng (1 lần)
        creation_fee = quota.creation_fee
        if user.credit_balance < creation_fee and not user.is_admin:
            raise InsufficientCreditsError(required=creation_fee, current=user.credit_balance)

        # 5. Lưu tệp âm thanh mẫu
        storage_base = Path(getattr(settings, "clone_storage_path", "./storage/clones"))
        samples_dir = storage_base / "samples"
        previews_dir = storage_base / "previews"
        samples_dir.mkdir(parents=True, exist_ok=True)
        previews_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(filename).suffix.lower() or ".mp3"
        if ext not in (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"):
            ext = ".mp3"

        safe_slug = re.sub(r"[^a-zA-Z0-9_]", "_", clean_name)[:20]
        unique_token = uuid.uuid4().hex[:10]
        voice_id = f"clone_{user.id}_{int(datetime.now().timestamp())}_{safe_slug}_{unique_token}"
        sample_file_path = str(samples_dir / f"{voice_id}_sample{ext}")

        with open(sample_file_path, "wb") as f_sample:
            f_sample.write(file_bytes)

        # Kiểm tra chất lượng mẫu âm thanh (5–30s, độ nhiễu, volume)
        val = await AudioService.validate_voice_sample(sample_file_path, min_duration=5.0, max_duration=30.0)
        if not val.get("valid"):
            if os.path.exists(sample_file_path):
                os.remove(sample_file_path)
            err_msg = val.get("error") or "Mẫu âm thanh không đạt tiêu chuẩn chất lượng."
            raise AppError("INVALID_AUDIO_SAMPLE", err_msg, 400)

        duration = val.get("duration", 0.0)
        quality_score = val.get("quality_score", 4.0)
        size_bytes = len(file_bytes)

        # 6. Gọi CloneProvider tạo profile
        try:
            clone_res = await self.provider.clone_voice(
                name=clean_name,
                audio_file_path=sample_file_path,
                description=description,
            )
            provider_voice_id = clone_res.get("provider_voice_id")
        except Exception as e:
            if os.path.exists(sample_file_path):
                os.remove(sample_file_path)
            logger.error(f"Lỗi khi gửi yêu cầu clone tới provider: {e}")
            raise AppError("PROVIDER_CLONE_ERROR", f"Không thể xử lý clone giọng lúc này: {str(e)}", 502)

        # 7. Khấu trừ Credit tạo giọng 1 lần
        if creation_fee > 0 and not user.is_admin:
            await CreditService.reserve(
                db=db,
                user_id=user.id,
                amount=creation_fee,
                ref_id=f"clone_{voice_id}",
                description=f"Phí tạo giọng clone 1 lần: {clean_name}",
            )

        # 8. Sinh mẫu phát thử (preview audio)
        target_preview_path = str(previews_dir / f"{voice_id}_preview.mp3")
        preview_path: Optional[str] = target_preview_path
        try:
            preview_text = f"Xin chào, đây là giọng đọc AI của {clean_name} đã được clone thành công trên Voxify."
            preview_bytes = await self.provider.synthesize(
                text=preview_text,
                provider_voice_id=provider_voice_id or voice_id,
                audio_sample_path=sample_file_path,
            )
            with open(target_preview_path, "wb") as f_prev:
                f_prev.write(preview_bytes)
        except Exception as e:
            logger.warning(f"Không thể sinh audio preview tự động cho {voice_id}: {e}")
            preview_path = None

        # 9. Lưu vào DB ClonedVoice
        cloned_voice = ClonedVoice(
            voice_id=voice_id,
            user_id=user.id,
            name=clean_name,
            description=description,
            audio_sample_path=sample_file_path,
            sample_duration=duration,
            sample_size_bytes=size_bytes,
            quality_score=quality_score,
            gender=gender,
            language=language,
            provider=self.provider.provider_name,
            provider_voice_id=provider_voice_id,
            preview_audio_path=preview_path,
            preview_audio_url=f"/api/voices/cloned/{voice_id}/preview" if preview_path else None,
            status="ready",
            is_active=True,
        )
        db.add(cloned_voice)
        await db.flush()

        # 10. Lưu audit log đồng ý (user_id, thời gian, IP, nội dung cam kết)
        consent_log = VoiceConsentLog(
            user_id=user.id,
            cloned_voice_id=cloned_voice.id,
            voice_name=clean_name,
            audio_sample_filename=filename,
            consent_text=CONSENT_MANDATORY_STATEMENT,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(consent_log)
        await db.commit()
        await db.refresh(cloned_voice)

        logger.info(f"Tạo thành công cloned voice #{cloned_voice.id} ({voice_id}) cho user #{user.id}")
        return cloned_voice

    @staticmethod
    async def list_user_cloned_voices(db: AsyncSession, user_id: int) -> List[ClonedVoice]:
        """Lấy danh sách tất cả giọng clone còn hoạt động của người dùng."""
        stmt = (
            select(ClonedVoice)
            .where(ClonedVoice.user_id == user_id)
            .where(ClonedVoice.is_active.is_(True))
            .order_by(ClonedVoice.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_cloned_voice(db: AsyncSession, voice_id: str, user_id: Optional[int] = None) -> Optional[ClonedVoice]:
        """Lấy chi tiết giọng clone."""
        stmt = select(ClonedVoice).where(ClonedVoice.voice_id == voice_id).where(ClonedVoice.is_active.is_(True))
        if user_id is not None:
            stmt = stmt.where(ClonedVoice.user_id == user_id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def update_cloned_voice(
        db: AsyncSession,
        voice_id: str,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ClonedVoice:
        """Đổi tên hoặc mô tả của giọng clone."""
        stmt = (
            select(ClonedVoice)
            .where(ClonedVoice.voice_id == voice_id)
            .where(ClonedVoice.user_id == user_id)
            .where(ClonedVoice.is_active.is_(True))
        )
        res = await db.execute(stmt)
        voice = res.scalar_one_or_none()
        if not voice:
            raise AppError("VOICE_NOT_FOUND", "Không tìm thấy giọng clone hoặc bạn không có quyền chỉnh sửa.", 404)

        if name is not None:
            clean_name = name.strip()
            if not clean_name:
                raise AppError("INVALID_NAME", "Tên giọng không được để trống.", 400)
            is_blocked, detected, block_reason = check_voice_name_against_blocklist(clean_name, description)
            if is_blocked and block_reason:
                raise AppError("CELEBRITY_VOICE_BLOCKED", block_reason, 400)
            voice.name = clean_name

        if description is not None:
            voice.description = description

        voice.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(voice)
        return voice

    async def delete_cloned_voice(self, db: AsyncSession, voice_id: str, user: User) -> bool:
        """
        Xóa giọng clone:
        1. Xóa khỏi provider
        2. Xóa tệp mẫu âm thanh gốc trên đĩa
        3. Xóa tệp preview
        4. Đánh dấu is_active = False, status = "deleted"
        => Đảm bảo khi xóa voice thì không còn dùng được nữa trong Studio.
        """
        stmt = (
            select(ClonedVoice)
            .where(ClonedVoice.voice_id == voice_id)
            .where(ClonedVoice.is_active.is_(True))
        )
        if not user.is_admin and user.role != "admin":
            stmt = stmt.where(ClonedVoice.user_id == user.id)

        res = await db.execute(stmt)
        voice = res.scalar_one_or_none()
        if not voice:
            raise AppError("VOICE_NOT_FOUND", "Không tìm thấy giọng clone cần xóa.", 404)

        # 1. Gọi provider xóa
        if voice.provider_voice_id:
            try:
                await self.provider.delete_cloned_voice(voice.provider_voice_id)
            except Exception as e:
                logger.warning(f"Lỗi khi xóa voice {voice.voice_id} trên provider: {e}")

        # 2. Xóa file mẫu âm thanh gốc trên đĩa
        if voice.audio_sample_path and os.path.exists(voice.audio_sample_path):
            try:
                os.remove(voice.audio_sample_path)
                logger.info(f"Đã xóa file mẫu gốc: {voice.audio_sample_path}")
            except Exception as e:
                logger.warning(f"Không thể xóa file mẫu {voice.audio_sample_path}: {e}")

        # 3. Xóa file preview
        if voice.preview_audio_path and os.path.exists(voice.preview_audio_path):
            try:
                os.remove(voice.preview_audio_path)
            except Exception as e:
                logger.warning(f"Không thể xóa file preview {voice.preview_audio_path}: {e}")

        # 4. Cập nhật trạng thái DB
        voice.is_active = False
        voice.status = "deleted"
        voice.updated_at = datetime.now(UTC)
        await db.commit()

        logger.info(f"Đã vô hiệu hóa và xóa dữ liệu giọng clone '{voice.name}' ({voice_id})")
        return True

    @staticmethod
    async def report_abuse(
        db: AsyncSession,
        voice_id: str,
        reason: str,
        description: str,
        reporter_user: Optional[User] = None,
        reporter_email: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> VoiceAbuseReport:
        """Tạo báo cáo vi phạm bản quyền / lạm dụng cho giọng clone."""
        if reason not in VALID_ABUSE_REASONS:
            raise AppError("INVALID_REASON", f"Lý do báo cáo không hợp lệ. Chọn một trong: {list(VALID_ABUSE_REASONS.keys())}", 400)

        stmt = select(ClonedVoice).where(ClonedVoice.voice_id == voice_id).where(ClonedVoice.is_active.is_(True))
        res = await db.execute(stmt)
        voice = res.scalar_one_or_none()
        if not voice:
            raise AppError("VOICE_NOT_FOUND", "Giọng clone không tồn tại hoặc đã bị xóa.", 404)

        report = VoiceAbuseReport(
            cloned_voice_id=voice.id,
            reporter_user_id=reporter_user.id if reporter_user else None,
            reporter_email=reporter_email or (reporter_user.email if reporter_user else None),
            reason=reason,
            description=description.strip(),
            status="pending",
            ip_address=ip_address,
        )
        db.add(report)

        # Nếu có từ 3 báo cáo pending trở lên, tạm gắn cờ reported
        count_stmt = (
            select(func.count(VoiceAbuseReport.id))
            .where(VoiceAbuseReport.cloned_voice_id == voice.id)
        )
        count_res = await db.execute(count_stmt)
        report_count = count_res.scalar() or 0
        if report_count >= 2:
            voice.status = "reported"

        await db.commit()
        await db.refresh(report)
        logger.info(f"Đã ghi nhận báo cáo lạm dụng #{report.id} cho voice {voice_id} (reason={reason})")
        return report

    async def synthesize_cloned_voice(
        self,
        db: AsyncSession,
        voice_id: str,
        user: Optional[User],
        text: str,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%",
    ) -> bytes:
        """Tổng hợp giọng nói cho giọng clone."""
        voice = await self.get_cloned_voice(db, voice_id)
        if not voice or not voice.is_active or voice.status != "ready":
            raise AppError(
                "VOICE_NOT_FOUND",
                "Giọng clone không tồn tại, đã bị xóa hoặc đang bị tạm khóa do vi phạm.",
                404,
            )

        # Kiểm tra quyền: giọng clone là riêng tư của user tạo ra
        if user and not user.is_admin and voice.user_id != user.id:
            raise AppError("FORBIDDEN_VOICE", "Bạn không có quyền sử dụng giọng clone cá nhân này.", 403)

        return await self.provider.synthesize(
            text=text,
            provider_voice_id=voice.provider_voice_id or voice.voice_id,
            audio_sample_path=voice.audio_sample_path,
            rate=rate,
            pitch=pitch,
            volume=volume,
        )
