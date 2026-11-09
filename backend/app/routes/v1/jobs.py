"""Public API v1: Tra cứu trạng thái và tiến độ Job TTS."""
import logging
from typing import Tuple

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.routes.v1.dependencies import get_v1_api_user
from app.schemas.api_key import V1JobResponse
from app.services.api_key_service import ApiKeyService
from app.services.tts_job_service import TTSJobService

logger = logging.getLogger(__name__)

router = APIRouter()
_job_service = TTSJobService()


@router.get(
    "/jobs/{job_id}",
    response_model=V1JobResponse,
    summary="Tra cứu trạng thái, tiến độ và link audio của Job TTS",
)
async def get_v1_job(
    job_id: int,
    request: Request,
    auth_data: Tuple[ApiKey, User] = Depends(get_v1_api_user),
    db: AsyncSession = Depends(get_db),
) -> V1JobResponse:
    """
    Tra cứu thông tin chi tiết của một Job TTS:
    - Trạng thái xử lý: queued | processing | done | failed
    - Tiến độ hoàn thành: 0 - 100%
    - Link tải audio (nếu done)
    - Thời lượng (duration) và số credit đã tiêu hao
    """
    api_key, user = auth_data

    # Tra cứu job với user_id (trừ admin)
    filter_user_id = None if user.is_admin else user.id
    job = await _job_service.get_job(db=db, job_id=job_id, user_id=filter_user_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy Job TTS #{job_id} hoặc bạn không có quyền truy cập.",
        )

    # Ghi log API usage
    client_ip = request.client.host if request.client else None
    await ApiKeyService.log_usage(
        db=db,
        api_key_id=api_key.id,
        user_id=user.id,
        endpoint=f"/v1/jobs/{job_id}",
        status_code=200,
        credits_used=0,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
    )

    audio_url = f"/api/tts/jobs/{job.id}/audio" if job.status == "done" and job.file_path else None

    return V1JobResponse(
        id=job.id,
        status="completed" if job.status == "done" else job.status,
        progress=job.progress,
        audio_url=audio_url,
        duration=job.duration,
        credits_used=job.credit_used,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
