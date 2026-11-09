"""Public API v1: Danh sách giọng đọc khả dụng (System + Cloned)."""
import logging
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.dependencies import get_tts_service
from app.models.api_key import ApiKey
from app.models.cloned_voice import ClonedVoice
from app.models.user import User
from app.routes.v1.dependencies import get_v1_api_user
from app.services.api_key_service import ApiKeyService
from app.services.tts_service import TTSService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/voices", summary="Lấy danh sách các giọng đọc khả dụng qua Public API")
async def list_v1_voices(
    request: Request,
    auth_data: Tuple[ApiKey, User] = Depends(get_v1_api_user),
    db: AsyncSession = Depends(get_db),
    tts_service: TTSService = Depends(get_tts_service),
) -> Dict[str, Any]:
    """
    Trả về danh sách giọng đọc:
    - Các giọng hệ thống tiêu chuẩn (ưu tiên tiếng Việt)
    - Các giọng clone độc quyền của tài khoản sở hữu API Key
    """
    api_key, user = auth_data

    # 1. Giọng hệ thống
    system_voices = await tts_service.get_voices()

    # 2. Giọng clone của user
    stmt_clones = (
        select(ClonedVoice)
        .where(ClonedVoice.user_id == user.id, ClonedVoice.is_active.is_(True), ClonedVoice.status == "ready")
        .order_by(ClonedVoice.created_at.desc())
    )
    res_clones = await db.execute(stmt_clones)
    cloned_records = res_clones.scalars().all()

    cloned_voices: List[Dict[str, Any]] = [
        {
            "id": c.voice_id,
            "name": f"{c.name} (Clone)",
            "short_name": c.voice_id,
            "gender": c.gender,
            "locale": c.language or "vi-VN",
            "is_vietnamese": True,
            "is_clone": True,
            "quality_score": c.quality_score,
            "credit_multiplier": 1.5,
        }
        for c in cloned_records
    ]

    all_voices = cloned_voices + system_voices

    # Ghi nhận log sử dụng
    client_ip = request.client.host if request.client else None
    await ApiKeyService.log_usage(
        db=db,
        api_key_id=api_key.id,
        user_id=user.id,
        endpoint="/v1/voices",
        status_code=200,
        credits_used=0,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
    )

    return {
        "total": len(all_voices),
        "cloned_count": len(cloned_voices),
        "system_count": len(system_voices),
        "voices": all_voices,
    }
