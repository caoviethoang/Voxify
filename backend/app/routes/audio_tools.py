"""Routes API cho Khung Công cụ Âm thanh (Audio Tools Framework) — Issue #20 / Prompt 19."""
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audio_tools.base import registry
from app.core.errors import AppError
from app.db import get_db
from app.dependencies import get_current_active_user
from app.models.audio_tool import AudioToolJob
from app.models.generation import Generation
from app.models.user import User
from app.schemas.audio_tool import (
    AudioToolCategoryGroup,
    AudioToolJobListResponse,
    AudioToolJobResponse,
    AudioToolListResponse,
    AudioToolResponse,
)
from app.services.audio_tool_service import AudioToolService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["Audio Tools"])
_tool_service = AudioToolService()


def _format_job_response(job: AudioToolJob) -> AudioToolJobResponse:
    parsed_params: Optional[Dict[str, Any]] = None
    if job.params:
        try:
            parsed_params = json.loads(job.params)
        except Exception:
            parsed_params = None

    has_output = bool(job.output_path and os.path.exists(job.output_path))
    return AudioToolJobResponse(
        id=job.id,
        tool_id=job.tool_id,
        user_id=job.user_id,
        status=job.status,
        progress=job.progress,
        input_filename=job.input_filename,
        input_duration=job.input_duration,
        params=parsed_params,
        output_filename=job.output_filename,
        output_duration=job.output_duration,
        output_size_bytes=job.output_size_bytes,
        output_url=f"/api/tools/jobs/{job.id}/stream" if has_output else None,
        stream_url=f"/api/tools/jobs/{job.id}/stream" if has_output else None,
        credit_used=job.credit_used,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("", response_model=AudioToolListResponse, summary="Danh sách công cụ âm thanh & JSON Schema")
async def list_audio_tools() -> AudioToolListResponse:
    """Trả về toàn bộ công cụ âm thanh, phân nhóm theo danh mục kèm JSON Schema cấu hình form."""
    tools = registry.list_tools()
    tool_dicts = [t.to_dict() for t in tools]
    cat_grouped = registry.get_by_category()

    categories_resp: Dict[str, AudioToolCategoryGroup] = {}
    for cat_key, cat_data in cat_grouped.items():
        categories_resp[cat_key] = AudioToolCategoryGroup(
            category=cat_data["category"],
            name_vi=cat_data["name_vi"],
            name_en=cat_data["name_en"],
            icon=cat_data["icon"],
            tools=[AudioToolResponse(**t) for t in cat_data["tools"]],
        )

    return AudioToolListResponse(
        total=len(tools),
        tools=[AudioToolResponse(**td) for td in tool_dicts],
        categories=categories_resp,
    )


@router.get("/jobs", response_model=AudioToolJobListResponse, summary="Lịch sử các tác vụ công cụ âm thanh của người dùng")
async def list_tool_jobs(
    tool_id: Optional[str] = Query(None, description="Lọc theo mã công cụ cụ thể"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AudioToolJobListResponse:
    """Tra cứu lịch sử các công việc xử lý công cụ âm thanh của tài khoản."""
    res = await _tool_service.list_user_jobs(
        db=db,
        user_id=current_user.id,
        tool_id=tool_id,
        limit=limit,
        offset=offset,
    )
    return AudioToolJobListResponse(
        total=res["total"],
        jobs=[_format_job_response(j) for j in res["jobs"]],
    )


@router.get("/jobs/{job_id}", response_model=AudioToolJobResponse, summary="Chi tiết & tiến độ tác vụ công cụ âm thanh")
async def get_tool_job_detail(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AudioToolJobResponse:
    """Kiểm tra trạng thái, tiến độ và thông tin tệp kết quả của tác vụ."""
    job = await _tool_service.get_job(db, job_id=job_id, user_id=current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy tác vụ công cụ này.")
    return _format_job_response(job)


@router.get("/jobs/{job_id}/stream", summary="Phát / Stream tệp âm thanh kết quả")
async def stream_tool_job_output(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Stream audio kết quả cho trình phát nhạc trên trình duyệt."""
    job = await _tool_service.get_job(db, job_id=job_id, user_id=current_user.id)
    if not job or not job.output_path or not os.path.exists(job.output_path):
        raise HTTPException(status_code=404, detail="Tệp âm thanh kết quả không tồn tại hoặc đã bị xóa.")

    ext = Path(job.output_path).suffix.lower()
    media_type = "audio/wav" if ext == ".wav" else "audio/mpeg"
    return FileResponse(
        job.output_path,
        media_type=media_type,
        filename=job.output_filename or os.path.basename(job.output_path),
    )


@router.get("/jobs/{job_id}/download", summary="Tải xuống tệp âm thanh kết quả")
async def download_tool_job_output(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Tải tệp âm thanh kết quả về máy tính."""
    job = await _tool_service.get_job(db, job_id=job_id, user_id=current_user.id)
    if not job or not job.output_path or not os.path.exists(job.output_path):
        raise HTTPException(status_code=404, detail="Tệp âm thanh kết quả không tồn tại hoặc đã bị xóa.")

    ext = Path(job.output_path).suffix.lower()
    media_type = "audio/wav" if ext == ".wav" else "audio/mpeg"
    return FileResponse(
        job.output_path,
        media_type=media_type,
        filename=job.output_filename or os.path.basename(job.output_path),
        headers={"Content-Disposition": f'attachment; filename="{job.output_filename or "audio"}"'},
    )


@router.get("/{tool_id}", response_model=AudioToolResponse, summary="Chi tiết một công cụ âm thanh")
async def get_tool_detail(tool_id: str) -> AudioToolResponse:
    """Lấy chi tiết và JSON Schema tham số của công cụ."""
    tool = registry.get(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy công cụ '{tool_id}'.")
    return AudioToolResponse(**tool.to_dict())


@router.post(
    "/{tool_id}/jobs",
    response_model=AudioToolJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo và thực thi công việc xử lý âm thanh",
)
async def create_tool_job(
    tool_id: str,
    params: str = Form("{}", description="Tham số JSON cấu hình công cụ"),
    audio_file: Optional[UploadFile] = File(None, description="Tệp âm thanh tải lên trực tiếp"),
    source_path: Optional[str] = Form(None, description="Đường dẫn tệp nguồn nội bộ"),
    source_generation_id: Optional[int] = Form(None, description="ID bản thu từ lịch sử TTS để tái sử dụng"),
    source_tool_job_id: Optional[int] = Form(None, description="ID tác vụ công cụ trước đó để liên kết công cụ"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AudioToolJobResponse:
    """
    Tạo job xử lý âm thanh:
    - Hỗ trợ tải tệp âm thanh lên trực tiếp
    - Hoặc liên kết từ tệp âm thanh TTS có sẵn (source_generation_id)
    - Hoặc liên kết từ kết quả của công cụ trước đó (source_tool_job_id)
    """
    # Parse params
    try:
        parsed_params: Dict[str, Any] = json.loads(params) if params else {}
    except Exception:
        raise HTTPException(status_code=400, detail="Tham số cấu hình params phải là định dạng chuỗi JSON hợp lệ.")

    file_bytes: Optional[bytes] = None
    filename: Optional[str] = None
    resolved_source_path: Optional[str] = source_path

    # Nếu upload file trực tiếp
    if audio_file:
        file_bytes = await audio_file.read()
        filename = audio_file.filename or "audio_input.mp3"
        if not file_bytes or len(file_bytes) < 100:
            raise HTTPException(status_code=400, detail="Tệp âm thanh tải lên không hợp lệ hoặc rỗng.")

    # Nếu liên kết từ Generation TTS
    elif source_generation_id:
        gen_res = await db.execute(
            select(Generation).where(
                Generation.id == source_generation_id,
                Generation.user_id == current_user.id,
            )
        )
        gen = gen_res.scalar_one_or_none()
        if not gen or not gen.file_path or not os.path.exists(gen.file_path):
            raise HTTPException(status_code=404, detail="Không tìm thấy tệp âm thanh nguồn từ bản thu TTS này.")
        resolved_source_path = gen.file_path

    # Nếu liên kết từ Tool Job trước đó ("Gửi sang công cụ khác")
    elif source_tool_job_id:
        prev_job = await _tool_service.get_job(db, job_id=source_tool_job_id, user_id=current_user.id)
        if not prev_job or not prev_job.output_path or not os.path.exists(prev_job.output_path):
            raise HTTPException(status_code=404, detail="Không tìm thấy tệp âm thanh kết quả từ tác vụ công cụ trước.")
        resolved_source_path = prev_job.output_path

    if not file_bytes and not resolved_source_path:
        raise HTTPException(
            status_code=400,
            detail="Vui lòng tải lên tệp âm thanh hoặc chỉ định tệp nguồn từ lịch sử xử lý.",
        )

    try:
        job = await _tool_service.create_and_execute_job(
            db=db,
            user=current_user,
            tool_id=tool_id,
            params=parsed_params,
            file_bytes=file_bytes,
            filename=filename,
            source_path=resolved_source_path,
        )
        return _format_job_response(job)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
