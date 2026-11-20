"""API Routes cho phân hệ Lồng tiếng phụ đề (Subtitle Dubbing - Issue #21)."""
import asyncio
import logging
import os
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db import AsyncSessionLocal, get_db
from app.dependencies import get_current_active_user, get_tts_service
from app.models.dubbing import DubbingJob
from app.models.user import User
from app.schemas.dubbing import (
    DubbingCreateJobRequest,
    DubbingJobResponse,
    DubbingParseRequest,
    DubbingParseResponse,
    DubbingPreviewCueRequest,
)
from app.services.dubbing_service import DubbingService
from app.services.storage_service import StorageService
from app.services.tts_service import TTSService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dubbing", tags=["Subtitle Dubbing"])
_storage_service = StorageService()


def _format_job_response(job: DubbingJob) -> DubbingJobResponse:
    """Format DubbingJob model sang DubbingJobResponse schema."""
    audio_download_url: Optional[str] = None
    zip_download_url: Optional[str] = None

    if job.status == "done":
        if job.output_audio_path and os.path.exists(job.output_audio_path):
            audio_download_url = f"/api/dubbing/jobs/{job.id}/audio"
        if job.output_zip_path and os.path.exists(job.output_zip_path):
            zip_download_url = f"/api/dubbing/jobs/{job.id}/zip"

    return DubbingJobResponse(
        id=job.id,
        user_id=job.user_id,
        title=job.title,
        subtitle_format=job.subtitle_format,
        target_format=job.target_format,
        default_voice=job.default_voice,
        status=job.status,
        progress=job.progress,
        total_cues=job.total_cues,
        char_count=job.char_count,
        credit_used=job.credit_used,
        cues_data=job.cues_data,
        output_audio_path=job.output_audio_path,
        output_zip_path=job.output_zip_path,
        background_audio_path=job.background_audio_path,
        ducking_volume=job.ducking_volume,
        error_message=job.error_message,
        duration=job.duration,
        created_at=job.created_at,
        updated_at=job.updated_at,
        audio_download_url=audio_download_url,
        zip_download_url=zip_download_url,
    )


@router.post("/parse", response_model=DubbingParseResponse)
async def parse_subtitles(
    req: DubbingParseRequest,
    current_user: User = Depends(get_current_active_user),
) -> DubbingParseResponse:
    """Phân tích nội dung thô phụ đề SRT/VTT thành danh sách Cue."""
    try:
        return DubbingService.parse_content(content=req.content, default_voice=req.default_voice)
    except Exception as e:
        logger.warning(f"Lỗi phân tích phụ đề: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng tệp phụ đề không hợp lệ: {str(e)}",
        )


@router.post("/upload-file", response_model=DubbingParseResponse)
async def upload_and_parse_subtitle_file(
    file: UploadFile = File(...),
    default_voice: str = Form("vi-VN-HoaiMyNeural"),
    current_user: User = Depends(get_current_active_user),
) -> DubbingParseResponse:
    """Tải lên file phụ đề (.srt hoặc .vtt) và phân tích thành các cue."""
    filename = file.filename or ""
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    if ext not in ("srt", "vtt"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ hỗ trợ tải lên tệp phụ đề định dạng .srt hoặc .vtt.",
        )

    content_bytes = await file.read()
    try:
        content_text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            content_text = content_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            content_text = content_bytes.decode("latin-1")

    return DubbingService.parse_content(content=content_text, default_voice=default_voice)


@router.post("/preview-cue")
async def preview_single_cue(
    req: DubbingPreviewCueRequest,
    current_user: User = Depends(get_current_active_user),
    tts_service: TTSService = Depends(get_tts_service),
) -> Response:
    """Nghe thử 1 câu phụ đề kèm thuật toán co dãn tempo thời gian thực."""
    try:
        audio_bytes, actual_dur, applied_tempo, warning = await DubbingService.preview_cue(
            text=req.text,
            voice=req.voice,
            tts_service=tts_service,
            target_duration=req.target_duration,
        )
        headers = {
            "Content-Type": "audio/mpeg",
            "X-Actual-Duration": str(round(actual_dur, 2)),
            "X-Adjusted-Tempo": str(round(applied_tempo, 2)) if applied_tempo else "1.0",
        }
        if warning:
            headers["X-Tempo-Warning"] = warning.encode("unicode_escape").decode("ascii")

        return Response(content=audio_bytes, media_type="audio/mpeg", headers=headers)
    except Exception as e:
        logger.error(f"Lỗi khi nghe thử cue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Không thể nghe thử câu phụ đề: {str(e)}",
        )


@router.post("/upload-bg-music")
async def upload_background_music(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Tải lên file nhạc nền để phục vụ Audio Ducking."""
    filename = file.filename or "bg_music.mp3"
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    if ext not in ("mp3", "wav", "m4a", "aac", "ogg"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tệp âm thanh nền phải có định dạng mp3, wav, m4a, aac hoặc ogg.",
        )

    # Lưu tạm vào thư mục storage
    os.makedirs("storage/temp_bg", exist_ok=True)
    temp_path = f"storage/temp_bg/user_{current_user.id}_{int(asyncio.get_event_loop().time())}_{filename}"
    content = await file.read()
    with open(temp_path, "wb") as f:
        f.write(content)

    return {"background_audio_path": temp_path, "filename": filename, "size": len(content)}


@router.post("/jobs", response_model=DubbingJobResponse, status_code=status.HTTP_201_CREATED)
async def create_dubbing_job(
    req: DubbingCreateJobRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tts_service: TTSService = Depends(get_tts_service),
) -> DubbingJobResponse:
    """Tạo tác vụ lồng tiếng phụ đề và kích hoạt tiến trình ngầm."""
    try:
        job = await DubbingService.create_dubbing_job(db=db, user_id=current_user.id, req=req)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    # Chạy tác vụ xử lý ngầm
    background_tasks.add_task(
        DubbingService.execute_dubbing_job,
        job.id,
        AsyncSessionLocal,
        tts_service,
        _storage_service,
    )

    return _format_job_response(job)


@router.get("/jobs", response_model=List[DubbingJobResponse])
async def list_dubbing_jobs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[DubbingJobResponse]:
    """Danh sách các tác vụ lồng tiếng của người dùng."""
    jobs = await DubbingService.list_user_jobs(db=db, user_id=current_user.id, limit=limit, offset=offset)
    return [_format_job_response(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=DubbingJobResponse)
async def get_dubbing_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DubbingJobResponse:
    """Lấy thông tin và tiến trình của một tác vụ lồng tiếng."""
    job = await DubbingService.get_job_by_id(db=db, job_id=job_id, user_id=current_user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tác vụ lồng tiếng.")
    return _format_job_response(job)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dubbing_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Xóa tác vụ lồng tiếng và dọn dẹp các tệp liên quan."""
    deleted = await DubbingService.delete_job(
        db=db, job_id=job_id, user_id=current_user.id, storage_service=_storage_service
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tác vụ lồng tiếng.")


@router.get("/jobs/{job_id}/audio")
async def download_master_audio(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FileResponse:
    """Tải file âm thanh Master của tác vụ lồng tiếng."""
    job = await DubbingService.get_job_by_id(db=db, job_id=job_id, user_id=current_user.id)
    if not job or not job.output_audio_path or not os.path.exists(job.output_audio_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tệp âm thanh chưa sẵn sàng hoặc không tồn tại."
        )

    filename = f"dubbing_{job.id}.{job.target_format}"
    media_type = "audio/mpeg" if job.target_format == "mp3" else "audio/wav"
    return FileResponse(path=job.output_audio_path, media_type=media_type, filename=filename)


@router.get("/jobs/{job_id}/zip")
async def download_cues_zip(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FileResponse:
    """Tải gói ZIP chứa toàn bộ file âm thanh các câu và phụ đề SRT."""
    job = await DubbingService.get_job_by_id(db=db, job_id=job_id, user_id=current_user.id)
    if not job or not job.output_zip_path or not os.path.exists(job.output_zip_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gói tệp ZIP chưa sẵn sàng hoặc không tồn tại."
        )

    filename = f"dubbing_cues_{job.id}.zip"
    return FileResponse(path=job.output_zip_path, media_type="application/zip", filename=filename)
