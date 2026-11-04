"""Route POST /api/tts — tổng hợp giọng nói và lưu Generation vào DB."""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.dependencies import get_tts_service, get_optional_current_user
from app.models.generation import Generation
from app.models.user import User
from app.schemas.tts import TTSRequest
from app.services.tts_service import TTSService
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tts", tags=["TTS"])

_storage_service = StorageService()


@router.post("", summary="Chuyển đổi văn bản thành file âm thanh MP3")
async def synthesize_speech(
    request: TTSRequest,
    tts_service: TTSService = Depends(get_tts_service),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Nhận văn bản, tổng hợp MP3 qua TTS provider, lưu record vào DB,
    trả về binary MP3.
    """
    clean_text = request.text.strip()
    if not clean_text:
        raise HTTPException(
            status_code=400,
            detail="Văn bản không được để trống. Vui lòng nhập nội dung cần đọc.",
        )

    try:
        audio_bytes = await tts_service.synthesize(
            text=clean_text,
            voice=request.voice.strip(),
            rate=request.rate or "+0%",
            pitch=request.pitch or "+0Hz",
            volume=request.volume or "+0%",
            preview=bool(request.preview),
        )

        # Lưu file audio và ghi lịch sử vào DB
        try:
            file_path, file_size = await _storage_service.save_audio(
                data=audio_bytes,
                voice=request.voice,
                is_preview=bool(request.preview),
            )
            generation = Generation(
                user_id=current_user.id if current_user else None,
                text=clean_text,
                voice=request.voice,
                rate=request.rate or "+0%",
                pitch=request.pitch or "+0Hz",
                volume=request.volume or "+0%",
                char_count=len(clean_text),
                file_path=file_path,
                file_size=file_size,
                is_preview=bool(request.preview),
                provider="edge",
            )
            db.add(generation)
            await db.flush()
            logger.info(f"Đã lưu Generation #{generation.id} ({len(clean_text)} ký tự)")
        except Exception as db_err:
            logger.warning(f"Không thể lưu Generation vào DB: {db_err}")

        filename = "preview.mp3" if request.preview else "speech.mp3"
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Content-Length": str(len(audio_bytes)),
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-cache",
            },
        )

    except ValueError as val_err:
        logger.warning(f"Lỗi tham số TTS: {val_err}")
        raise HTTPException(status_code=400, detail=str(val_err))
    except RuntimeError as run_err:
        logger.error(f"Lỗi runtime TTS: {run_err}")
        raise HTTPException(
            status_code=502,
            detail=f"Lỗi dịch vụ tổng hợp giọng nói: {str(run_err)}",
        )
    except Exception as e:
        logger.exception(f"Lỗi không xác định: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Đã xảy ra lỗi hệ thống: {str(e)}",
        )
