"""Route GET /api/config — trả về cấu hình frontend cần biết."""
from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(prefix="/api/config", tags=["Config"])


@router.get("", summary="Lấy cấu hình ứng dụng")
async def get_app_config():
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "max_text_length": settings.max_chars,
        "max_chars": settings.max_chars,
        "chunk_size": settings.chunk_size,
        "default_voice": settings.default_voice,
        "tts_provider": settings.tts_provider,
    }
