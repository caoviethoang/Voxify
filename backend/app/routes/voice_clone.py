"""Routes /api/voices/clone — Tạo, quản lý, nghe thử và báo cáo lạm dụng Clone giọng nói."""
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db import get_db
from app.dependencies import get_current_active_user, get_optional_current_user
from app.models.cloned_voice import ClonedVoice
from app.models.user import User
from app.schemas.voice_clone import (
    ClonedVoiceListResponse,
    ClonedVoiceResponse,
    VoiceAbuseReportCreateRequest,
    VoiceAbuseReportResponse,
    VoiceCloneQuota,
    VoiceCloneUpdateRequest,
)
from app.services.voice_clone_service import VoiceCloneService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voices", tags=["Voice Cloning"])
_clone_service = VoiceCloneService()


def _format_cloned_voice_response(voice: ClonedVoice) -> ClonedVoiceResponse:
    has_preview = voice.preview_audio_path and os.path.exists(voice.preview_audio_path)
    has_sample = voice.audio_sample_path and os.path.exists(voice.audio_sample_path)
    return ClonedVoiceResponse(
        id=voice.id,
        voice_id=voice.voice_id,
        user_id=voice.user_id,
        name=voice.name,
        description=voice.description,
        sample_duration=round(voice.sample_duration, 2),
        sample_size_bytes=voice.sample_size_bytes,
        quality_score=voice.quality_score,
        gender=voice.gender,
        language=voice.language,
        provider=voice.provider,
        status=voice.status,
        is_active=voice.is_active,
        created_at=voice.created_at,
        updated_at=voice.updated_at,
        preview_url=f"/api/voices/cloned/{voice.voice_id}/preview" if has_preview else None,
        sample_url=f"/api/voices/cloned/{voice.voice_id}/sample" if has_sample else None,
    )


@router.get("/clone/limits", response_model=VoiceCloneQuota, summary="Xem hạn mức và chi phí clone giọng của tài khoản")
async def get_voice_clone_limits(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Trả về số lượng voice đã dùng, hạn mức gói cước, phí tạo 1 lần và hệ số nhân credit."""
    return await _clone_service.get_user_quota(db, current_user)


@router.post("/clone", response_model=ClonedVoiceResponse, status_code=status.HTTP_201_CREATED, summary="Tạo giọng clone mới từ mẫu âm thanh")
async def create_voice_clone(
    request: Request,
    name: str = Form(..., description="Tên hiển thị của giọng clone"),
    description: Optional[str] = Form(None, description="Mô tả phong cách hoặc mục đích giọng"),
    consent_accepted: bool = Form(..., description="Cam kết bản quyền & chủ quyền giọng nói"),
    gender: str = Form("unspecified", description="Giới tính giọng: male | female | unspecified"),
    language: str = Form("vi-VN", description="Ngôn ngữ mẫu: vi-VN, en-US..."),
    audio_file: UploadFile = File(..., description="Tệp âm thanh mẫu hoặc bản ghi âm 5 giây – 3 phút"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Tạo Voice Clone:
    - Bắt buộc kiểm tra cam kết bản quyền
    - Chặn tên người nổi tiếng / chính trị gia
    - Kiểm tra độ dài (5s – 3 phút) và chất lượng âm thanh (volumedetect)
    - Trừ phí tạo 1 lần (500 credits)
    - Lưu audit log đồng ý (user_id, IP, User-Agent, thời gian)
    """
    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Tên giọng đọc không được để trống.")

    # Đọc nội dung tệp
    content = await audio_file.read()
    if not content or len(content) < 1000:
        raise HTTPException(status_code=400, detail="Tệp âm thanh không hợp lệ hoặc quá nhỏ.")

    # Lấy IP & User Agent
    client_ip = request.client.host if request.client else None
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    user_agent = request.headers.get("user-agent", "")

    try:
        voice = await _clone_service.create_cloned_voice(
            db=db,
            user=current_user,
            name=clean_name,
            description=description,
            file_bytes=content,
            filename=audio_file.filename or "sample.mp3",
            consent_accepted=consent_accepted,
            gender=gender,
            language=language,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return _format_cloned_voice_response(voice)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/cloned", response_model=ClonedVoiceListResponse, summary="Danh sách giọng clone của người dùng hiện tại")
async def list_cloned_voices(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Trả về danh sách giọng clone hoạt động của tài khoản kèm hạn mức gói."""
    voices = await _clone_service.list_user_cloned_voices(db, current_user.id)
    quota = await _clone_service.get_user_quota(db, current_user)
    formatted = [_format_cloned_voice_response(v) for v in voices]
    return ClonedVoiceListResponse(
        total=len(formatted),
        quota=quota,
        voices=formatted,
    )


@router.get("/cloned/{voice_id}", response_model=ClonedVoiceResponse, summary="Chi tiết giọng clone")
async def get_cloned_voice_detail(
    voice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    voice = await _clone_service.get_cloned_voice(db, voice_id)
    if not voice or not voice.is_active:
        raise HTTPException(status_code=404, detail="Không tìm thấy giọng clone này.")
    if not current_user.is_admin and voice.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập giọng clone này.")
    return _format_cloned_voice_response(voice)


@router.patch("/cloned/{voice_id}", response_model=ClonedVoiceResponse, summary="Đổi tên / mô tả giọng clone")
async def update_cloned_voice(
    voice_id: str,
    payload: VoiceCloneUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        voice = await _clone_service.update_cloned_voice(
            db=db,
            voice_id=voice_id,
            user_id=current_user.id,
            name=payload.name,
            description=payload.description,
        )
        return _format_cloned_voice_response(voice)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete("/cloned/{voice_id}", summary="Xóa giọng clone (xóa cả file mẫu gốc)")
async def delete_cloned_voice(
    voice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Xóa vĩnh viễn giọng clone, xóa file mẫu gốc và file preview trên đĩa."""
    try:
        await _clone_service.delete_cloned_voice(db, voice_id, current_user)
        return {"success": True, "message": "Đã xóa giọng clone và tệp mẫu gốc thành công."}
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/cloned/{voice_id}/preview", summary="Phát mẫu thử của giọng clone")
async def stream_preview_audio(
    voice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    voice = await _clone_service.get_cloned_voice(db, voice_id)
    if not voice or not voice.is_active:
        raise HTTPException(status_code=404, detail="Giọng clone không tồn tại hoặc đã bị xóa.")

    if not voice.preview_audio_path or not os.path.exists(voice.preview_audio_path):
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp nghe thử của giọng này.")

    return FileResponse(
        voice.preview_audio_path,
        media_type="audio/mpeg",
        filename=f"{voice.name}_preview.mp3",
    )


@router.get("/cloned/{voice_id}/sample", summary="Phát tệp mẫu âm thanh thu âm gốc (chỉ chủ giọng hoặc admin)")
async def stream_sample_audio(
    voice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    voice = await _clone_service.get_cloned_voice(db, voice_id)
    if not voice or not voice.is_active:
        raise HTTPException(status_code=404, detail="Giọng clone không tồn tại hoặc đã bị xóa.")

    if not current_user.is_admin and voice.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Chỉ chủ sở hữu giọng mới có quyền nghe tệp mẫu gốc.")

    if not voice.audio_sample_path or not os.path.exists(voice.audio_sample_path):
        raise HTTPException(status_code=404, detail="Tệp mẫu âm thanh gốc không còn tồn tại trên máy chủ.")

    ext = Path(voice.audio_sample_path).suffix.lower()
    media_type = "audio/wav" if ext == ".wav" else "audio/mpeg"
    return FileResponse(
        voice.audio_sample_path,
        media_type=media_type,
        filename=os.path.basename(voice.audio_sample_path),
    )


@router.post("/cloned/{voice_id}/report", response_model=VoiceAbuseReportResponse, summary="Báo cáo lạm dụng / vi phạm bản quyền")
async def report_voice_abuse(
    voice_id: str,
    payload: VoiceAbuseReportCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Cơ chế báo cáo lạm dụng: mạo danh chính trị gia, người nổi tiếng, không có sự đồng ý hoặc phát tán tin giả."""
    client_ip = request.client.host if request.client else None
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()

    try:
        report = await _clone_service.report_abuse(
            db=db,
            voice_id=voice_id,
            reason=payload.reason,
            description=payload.description,
            reporter_user=current_user,
            reporter_email=payload.reporter_email,
            ip_address=client_ip,
        )
        return report
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
