"""Route POST /api/tts — tổng hợp giọng nói, trừ/hoàn credit và lưu Generation vào DB."""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.dependencies import get_tts_service, get_optional_current_user, get_current_active_user
from app.models.generation import Generation
from app.models.user import User
from app.schemas.tts import TTSRequest
from app.services.tts_service import TTSService
from app.services.storage_service import StorageService
from app.services.credit_service import CreditService, InsufficientCreditsError

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
    Nhận văn bản:
    1. Kiểm tra số dư credit và khấu trừ trước (reserve)
    2. Chạy TTS service tổng hợp audio
    3. Nếu thất bại, tự động hoàn trả credit (refund)
    4. Nếu thành công, lưu file, ghi Generation và trả về file MP3 kèm header X-Credit-Balance
    """
    clean_text = request.text.strip()
    if not clean_text:
        raise HTTPException(
            status_code=400,
            detail="Văn bản không được để trống. Vui lòng nhập nội dung cần đọc.",
        )

    from app.config import get_settings
    settings = get_settings()
    if len(clean_text) > settings.max_chars:
        raise HTTPException(
            status_code=400,
            detail=f"Văn bản vượt quá giới hạn tối đa {settings.max_chars:,} ký tự.",
        )

    is_preview = bool(request.preview)
    cost = 0
    tx = None

    # Khấu trừ credit nếu không phải bản nghe thử và có user
    if not is_preview:
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail="Vui lòng đăng nhập để sử dụng tính năng tạo giọng nói đầy đủ.",
            )

        cost = CreditService.calculate_cost(len(clean_text), provider="edge", voice=request.voice)
        try:
            tx = await CreditService.reserve(
                db=db,
                user_id=current_user.id,
                amount=cost,
                ref_id="pending_tts",
                description=f"Tạo giọng nói ({len(clean_text)} ký tự - {request.voice})",
            )
            await db.commit()
            logger.info(f"User #{current_user.id} đã reserve {cost} credit cho job TTS")
        except InsufficientCreditsError as credit_err:
            raise HTTPException(
                status_code=402,
                detail=credit_err.message,
            )

    try:
        # Thực hiện tổng hợp giọng nói
        audio_bytes = await tts_service.synthesize(
            text=clean_text,
            voice=request.voice.strip(),
            rate=request.rate or "+0%",
            pitch=request.pitch or "+0Hz",
            volume=request.volume or "+0%",
            preview=is_preview,
        )

        # Lưu file audio và ghi lịch sử vào DB
        file_path, file_size = await _storage_service.save_audio(
            data=audio_bytes,
            voice=request.voice,
            is_preview=is_preview,
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
            is_preview=is_preview,
            provider="edge",
        )
        db.add(generation)

        # Cập nhật ref_id cho giao dịch nếu có
        if tx:
            tx.ref_id = f"gen_{generation.id}"

        await db.commit()
        logger.info(f"Đã lưu Generation #{generation.id} ({len(clean_text)} ký tự)")

        # Lấy số dư mới nhất để trả về qua header
        new_balance = current_user.credit_balance if current_user else 0

        filename = "preview.mp3" if is_preview else "speech.mp3"
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Content-Length": str(len(audio_bytes)),
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-cache",
                "X-Credit-Balance": str(new_balance),
                "X-Credit-Used": str(cost),
            },
        )

    except Exception as exc:
        # NẾU CÓ LỖI: Tự động hoàn lại số credit đã trừ trước đó (refund)
        if tx and cost > 0 and current_user:
            try:
                await CreditService.refund(
                    db=db,
                    user_id=current_user.id,
                    amount=cost,
                    ref_id=str(tx.id),
                    reason=f"Hoàn trả credit do lỗi xử lý: {str(exc)[:100]}",
                )
                await db.commit()
                logger.warning(f"Đã hoàn trả {cost} credit cho User #{current_user.id} sau sự cố job TTS")
            except Exception as refund_err:
                logger.error(f"Lỗi khi thực hiện hoàn credit: {refund_err}")

        if isinstance(exc, HTTPException):
            raise exc
        if isinstance(exc, ValueError):
            logger.warning(f"Lỗi tham số TTS: {exc}")
            raise HTTPException(status_code=400, detail=str(exc))
        if isinstance(exc, RuntimeError):
            logger.error(f"Lỗi runtime TTS: {exc}")
            raise HTTPException(
                status_code=502,
                detail=f"Lỗi dịch vụ tổng hợp giọng nói: {str(exc)}",
            )

        logger.exception(f"Lỗi không xác định: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi máy chủ nội bộ khi tạo âm thanh: {str(exc)}",
        )
