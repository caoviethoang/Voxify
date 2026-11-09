"""Public API v1: Chuyển đổi văn bản thành giọng nói (Sync & Async)."""
import logging
from datetime import datetime
from typing import Any, Optional, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db import get_db
from app.dependencies import get_tts_service
from app.models.api_key import ApiKey
from app.models.cloned_voice import ClonedVoice
from app.models.generation import Generation
from app.models.user import User
from app.routes.v1.dependencies import get_v1_api_user
from app.schemas.api_key import V1TTSRequest, V1TTSResponse
from app.services.api_key_service import ApiKeyService
from app.services.audio_service import AudioService
from app.services.credit_service import CreditService, InsufficientCreditsError
from app.services.storage_service import StorageService
from app.services.tts_job_service import TTSJobService
from app.services.tts_service import TTSService
from app.services.voice_clone_service import VoiceCloneService

logger = logging.getLogger(__name__)

router = APIRouter()
_storage_service = StorageService()
_clone_service = VoiceCloneService()


@router.post(
    "/tts",
    response_model=Optional[V1TTSResponse],
    summary="Tổng hợp giọng nói qua Public API v1 (Hỗ trợ Sync và Async)",
    status_code=status.HTTP_200_OK,
)
async def create_v1_tts(
    request: Request,
    response: Response,
    payload: V1TTSRequest,
    accept: Optional[str] = Header(None),
    download: bool = Query(False, description="Nếu true, trả về trực tiếp luồng audio file thay vì JSON"),
    auth_data: Tuple[ApiKey, User] = Depends(get_v1_api_user),
    db: AsyncSession = Depends(get_db),
    tts_service: TTSService = Depends(get_tts_service),
) -> Any:
    """
    Điểm cuối chuyển đổi văn bản sang âm thanh:
    - mode="async": Tạo job ngầm, khấu trừ credit, trả job_id (HTTP 202) và gửi Webhook khi xong.
    - mode="sync": Khấu trừ credit, tổng hợp ngay và trả kết quả JSON hoặc file stream (HTTP 200).
    """
    api_key, user = auth_data
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Văn bản không được để trống.")

    client_ip = request.client.host if request.client else None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    # ------------------------------------------------------------------
    # 1. Chế độ BẤT ĐỒNG BỘ (Async Job)
    # ------------------------------------------------------------------
    if payload.mode.lower() == "async":
        job_service = TTSJobService(tts_service=tts_service, storage_service=_storage_service)
        try:
            job = await job_service.create_job(
                db=db,
                user=user,
                text=text,
                voice=payload.voice,
                rate=payload.rate,
                pitch=payload.pitch,
                volume=payload.volume,
                output_format="mp3",
                apply_dict=True,
                webhook_url=payload.webhook_url,
            )
        except InsufficientCreditsError as e:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Số dư credit không đủ ({e.current}/{e.required}). Vui lòng nạp thêm credit.",
            )
        except AppError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo job TTS async: {e}")
            raise HTTPException(status_code=500, detail="Không thể tạo job TTS lúc này.")

        # Ghi nhận log sử dụng
        await ApiKeyService.log_usage(
            db=db,
            api_key_id=api_key.id,
            user_id=user.id,
            endpoint="/v1/tts (async)",
            status_code=202,
            credits_used=job.credit_used,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
        )

        response.status_code = status.HTTP_202_ACCEPTED
        return V1TTSResponse(
            job_id=job.id,
            status="processing",
            audio_url=None,
            duration=None,
            credits_used=job.credit_used,
            message="Job TTS đã được đưa vào hàng đợi xử lý.",
        )

    # ------------------------------------------------------------------
    # 2. Chế độ ĐỒNG BỘ (Sync)
    # ------------------------------------------------------------------
    char_count = len(text)
    cost = CreditService.calculate_cost(char_count, voice=payload.voice)

    # Khấu trừ trước credit (Reserve)
    tx = None
    try:
        tx = await CreditService.reserve(
            db=db,
            user_id=user.id,
            amount=cost,
            description=f"Public API v1 Sync TTS ({char_count} ký tự - {payload.voice})",
        )
    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Số dư credit không đủ ({e.current}/{e.required}). Vui lòng nạp thêm credit.",
        )

    # Kiểm tra & tổng hợp âm thanh
    try:
        if payload.voice.startswith("clone_"):
            # Kiểm tra quyền với giọng clone
            stmt_clone = (
                select(ClonedVoice)
                .where(ClonedVoice.voice_id == payload.voice, ClonedVoice.is_active.is_(True))
            )
            res_clone = await db.execute(stmt_clone)
            clone_rec = res_clone.scalar_one_or_none()
            if not clone_rec or clone_rec.status != "ready":
                raise HTTPException(status_code=404, detail="Giọng clone không tồn tại hoặc chưa sẵn sàng.")
            if not user.is_admin and clone_rec.user_id != user.id:
                raise HTTPException(status_code=403, detail="Bạn không có quyền sử dụng giọng clone này.")

            audio_bytes = await _clone_service.synthesize_cloned_voice(
                db=db,
                voice_id=payload.voice,
                user=user,
                text=text,
                rate=payload.rate,
                pitch=payload.pitch,
                volume=payload.volume,
            )
        else:
            audio_bytes = await tts_service.synthesize(
                text=text,
                voice=payload.voice,
                rate=payload.rate,
                pitch=payload.pitch,
                volume=payload.volume,
                preview=False,
            )

        # Lưu file audio vào storage
        file_path, file_size = await _storage_service.save_audio(
            data=audio_bytes,
            voice=payload.voice,
            is_preview=False,
        )

        # Đo thời lượng
        duration = AudioService.measure_duration(file_path)
        if duration <= 0:
            duration = max(0.5, char_count / 12.0)

        # Tạo bản ghi Generation hoàn tất
        gen = Generation(
            user_id=user.id,
            text=text,
            voice=payload.voice,
            rate=payload.rate,
            pitch=payload.pitch,
            volume=payload.volume,
            char_count=char_count,
            format="mp3",
            file_path=file_path,
            file_size=file_size,
            duration=round(duration, 2),
            status="done",
            progress=100,
            credit_used=cost,
            is_preview=False,
            provider="clone" if payload.voice.startswith("clone_") else "edge",
            title=f"API v1 Sync TTS - {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        )
        db.add(gen)
        await db.commit()
        await db.refresh(gen)

        if tx:
            tx.ref_id = f"gen_{gen.id}"
            await db.commit()

        # Ghi nhận log thành công
        await ApiKeyService.log_usage(
            db=db,
            api_key_id=api_key.id,
            user_id=user.id,
            endpoint="/v1/tts (sync)",
            status_code=200,
            credits_used=cost,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
        )

        # Nếu client yêu cầu luồng file âm thanh trực tiếp (hoặc cURL trực tiếp)
        wants_audio = download or (accept and "audio" in accept.lower())
        if wants_audio:
            return Response(
                content=audio_bytes,
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": f'attachment; filename="speech_{gen.id}.mp3"',
                    "X-Duration": str(gen.duration),
                    "X-Job-Id": str(gen.id),
                    "X-Credits-Used": str(cost),
                },
            )

        return V1TTSResponse(
            job_id=gen.id,
            status="completed",
            audio_url=f"/api/tts/jobs/{gen.id}/audio",
            duration=gen.duration,
            credits_used=cost,
            message="Tạo giọng nói thành công.",
        )

    except HTTPException:
        # Hoàn tiền nếu HTTPException
        if cost > 0:
            await CreditService.refund(
                db=db,
                user_id=user.id,
                amount=cost,
                reason="Hoàn trả credit cho API v1 sync lỗi",
            )
        raise
    except Exception as exc:
        logger.error(f"Lỗi khi xử lý sync TTS: {exc}", exc_info=True)
        if cost > 0:
            await CreditService.refund(
                db=db,
                user_id=user.id,
                amount=cost,
                reason=f"Hoàn trả credit cho API v1 sync lỗi: {str(exc)[:100]}",
            )
        raise HTTPException(status_code=500, detail=f"Lỗi khi tổng hợp giọng nói: {str(exc)}")
