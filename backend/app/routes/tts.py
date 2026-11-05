"""Route /api/tts — tổng hợp giọng nói đồng bộ, background jobs, trừ/hoàn credit và phụ đề."""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.dependencies import get_tts_service, get_optional_current_user, get_current_active_user
from app.models.generation import Generation
from app.models.user import User
from app.schemas.tts import (
    TTSRequest,
    TTSJobCreateRequest,
    TTSJobResponse,
)
from app.services.tts_service import TTSService
from app.services.tts_job_service import TTSJobService
from app.services.storage_service import StorageService
from app.services.audio_service import AudioService
from app.services.credit_service import CreditService, InsufficientCreditsError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tts", tags=["TTS"])

_storage_service = StorageService()
_job_service = TTSJobService(storage_service=_storage_service)


def _to_job_response(gen: Generation) -> TTSJobResponse:
    """Chuyển đổi Generation model sang TTSJobResponse schema kèm URL tải."""
    has_audio = gen.status == "done" and gen.file_path and os.path.exists(gen.file_path)
    has_srt = gen.status == "done" and gen.srt_path and os.path.exists(gen.srt_path)
    has_vtt = gen.status == "done" and gen.vtt_path and os.path.exists(gen.vtt_path)

    return TTSJobResponse(
        id=gen.id,
        status=gen.status,
        progress=gen.progress,
        text=gen.text or "",
        char_count=gen.char_count,
        duration=round(gen.duration, 2),
        format=gen.format or "mp3",
        credit_used=gen.credit_used,
        voice=gen.voice,
        rate=gen.rate or "+0%",
        pitch=gen.pitch or "+0Hz",
        volume=gen.volume or "+0%",
        error_message=gen.error_message,
        audio_url=f"/api/tts/jobs/{gen.id}/audio" if has_audio else None,
        srt_url=f"/api/tts/jobs/{gen.id}/subtitles?format=srt" if has_srt else None,
        vtt_url=f"/api/tts/jobs/{gen.id}/subtitles?format=vtt" if has_vtt else None,
        created_at=gen.created_at,
        updated_at=gen.updated_at or gen.created_at,
    )


# -----------------------------------------------------------------------------
# Background Jobs API (Prompt 5)
# -----------------------------------------------------------------------------

@router.post("/jobs", response_model=TTSJobResponse, status_code=status.HTTP_202_ACCEPTED, summary="Tạo Job TTS bất đồng bộ")
async def create_tts_job(
    req: TTSJobCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Tạo job bất đồng bộ:
    1. Kiểm tra văn bản và khấu trừ credit ngay lập tức (reserve).
    2. Đưa vào hàng đợi worker xử lý ngầm (tách câu ~2500 ký tự, ghép ffmpeg, tạo SRT/VTT).
    3. Trả về thông tin job để client polling / theo dõi tiến độ.
    """
    clean_text = req.text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Văn bản không được để trống.")

    settings = get_settings()
    # Hỗ trợ văn bản dài cho background job (tối đa 100.000 ký tự)
    max_job_chars = 100000
    if len(clean_text) > max_job_chars:
        raise HTTPException(
            status_code=400,
            detail=f"Văn bản vượt quá giới hạn tối đa {max_job_chars:,} ký tự.",
        )

    try:
        job = await _job_service.create_job(
            db=db,
            user=current_user,
            text=clean_text,
            voice=req.voice,
            rate=req.rate or "+0%",
            pitch=req.pitch or "+0Hz",
            volume=req.volume or "+0%",
            output_format=req.format or "mp3",
            apply_dict=req.apply_dictionary if req.apply_dictionary is not None else True,
        )
        return _to_job_response(job)
    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=402,
            detail=f"Số dư credit không đủ ({e.current}/{e.required}). Vui lòng nạp thêm credit.",
        )
    except Exception as exc:
        logger.error(f"Lỗi khi tạo Job TTS: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/jobs/{job_id}", response_model=TTSJobResponse, summary="Tra cứu trạng thái và tiến độ Job TTS")
async def get_tts_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Lấy trạng thái tiến độ hiện tại của job (queued, processing, done, failed)."""
    user_id = current_user.id if current_user else None
    job = await _job_service.get_job(db, job_id, user_id=user_id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy job TTS.")
    return _to_job_response(job)


@router.get("/jobs", response_model=List[TTSJobResponse], summary="Danh sách Job gần đây của người dùng")
async def list_recent_tts_jobs(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Lấy danh sách các job TTS gần nhất của người dùng."""
    jobs = await _job_service.list_recent_jobs(db, current_user.id, limit=limit)
    return [_to_job_response(j) for j in jobs]


@router.get("/jobs/{job_id}/audio", summary="Tải hoặc phát file âm thanh của Job")
async def get_job_audio(
    job_id: int,
    download: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Phát hoặc tải file âm thanh MP3/WAV hoàn chỉnh của Job."""
    job = await _job_service.get_job(db, job_id)
    if not job or job.status != "done" or not job.file_path or not os.path.exists(job.file_path):
        raise HTTPException(status_code=404, detail="File âm thanh chưa sẵn sàng hoặc không tồn tại.")

    ext = job.format.lower()
    media_type = "audio/wav" if ext == "wav" else "audio/mpeg"
    filename = f"speech_{job.id}.{ext}"
    disposition = "attachment" if download else "inline"

    return FileResponse(
        path=job.file_path,
        media_type=media_type,
        filename=filename,
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            "Accept-Ranges": "bytes",
        },
    )


@router.get("/jobs/{job_id}/subtitles", summary="Tải file phụ đề SRT hoặc VTT của Job")
async def get_job_subtitles(
    job_id: int,
    format: str = Query(default="srt", pattern="^(srt|vtt)$"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Tải file phụ đề đồng bộ mốc thời gian (SRT hoặc WebVTT)."""
    job = await _job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi âm thanh.")

    sub_path = job.vtt_path if format == "vtt" else job.srt_path

    # Nếu file phụ đề chưa có trên đĩa, tự động ước lượng và tạo từ văn bản & thời lượng
    if not sub_path or not os.path.exists(sub_path):
        duration = job.duration
        if duration <= 0 and job.file_path and os.path.exists(job.file_path):
            duration = AudioService.measure_duration(job.file_path)
            job.duration = duration
        if duration <= 0:
            duration = max(1.0, len(job.text) / 12.0)

        Path("storage/audio").mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        srt_path = str(Path("storage/audio") / f"subtitles_job_{job.id}_{timestamp}.srt")
        vtt_path = str(Path("storage/audio") / f"subtitles_job_{job.id}_{timestamp}.vtt")

        AudioService.generate_estimated_subtitles(
            text=job.text,
            total_duration=duration,
            srt_path=srt_path,
            vtt_path=vtt_path,
        )
        job.srt_path = srt_path
        job.vtt_path = vtt_path
        await db.commit()
        sub_path = vtt_path if format == "vtt" else srt_path

    media_type = "text/vtt" if format == "vtt" else "application/x-subrip"
    filename = f"subtitles_{job.id}.{format}"
    return FileResponse(
        path=sub_path,
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# -----------------------------------------------------------------------------
# Đồng bộ / Preview TTS API (Giữ nguyên cho tương thích & nghe thử 200 ký tự)
# -----------------------------------------------------------------------------

@router.post("", summary="Chuyển đổi văn bản thành file âm thanh MP3 (đồng bộ / nghe thử)")
async def synthesize_speech(
    request: TTSRequest,
    tts_service: TTSService = Depends(get_tts_service),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    clean_text = request.text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Văn bản không được để trống.")

    settings = get_settings()
    if len(clean_text) > settings.max_chars:
        raise HTTPException(
            status_code=400,
            detail=f"Văn bản vượt quá giới hạn tối đa {settings.max_chars:,} ký tự.",
        )

    is_preview = bool(request.preview)
    if is_preview:
        clean_text = clean_text[:200]

    cost = 0
    tx = None
    if current_user and not is_preview:
        cost = CreditService.calculate_cost(len(clean_text), provider="edge", voice=request.voice)
        try:
            tx = await CreditService.reserve(
                db=db,
                user_id=current_user.id,
                amount=cost,
                description=f"Tạo giọng nói ({len(clean_text)} ký tự - {request.voice})",
            )
        except InsufficientCreditsError as e:
            raise HTTPException(
                status_code=402,
                detail=f"Số dư credit không đủ ({e.current}/{e.required}). Vui lòng nạp thêm credit.",
            )

    try:
        audio_bytes = await tts_service.synthesize(
            text=clean_text,
            voice=request.voice.strip(),
            rate=request.rate or "+0%",
            pitch=request.pitch or "+0Hz",
            volume=request.volume or "+0%",
            preview=is_preview,
        )

        file_path, file_size = await _storage_service.save_audio(
            data=audio_bytes,
            voice=request.voice,
            is_preview=is_preview,
        )
        duration = AudioService.measure_duration(file_path)

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
            duration=duration,
            status="done",
            progress=100,
            credit_used=cost,
            format="mp3",
            is_preview=is_preview,
            provider="edge",
        )
        db.add(generation)

        if tx:
            tx.ref_id = f"gen_{generation.id}"

        await db.commit()

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
                "X-Duration": str(duration),
            },
        )

    except Exception as exc:
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
            except Exception as refund_err:
                logger.error(f"Lỗi khi hoàn credit: {refund_err}")

        if isinstance(exc, HTTPException):
            raise exc
        if isinstance(exc, ValueError):
            raise HTTPException(status_code=400, detail=str(exc))
        if isinstance(exc, RuntimeError):
            raise HTTPException(status_code=502, detail=f"Lỗi dịch vụ tổng hợp giọng nói: {str(exc)}")

        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ nội bộ: {str(exc)}")
