from typing import Any, Dict
from fastapi import APIRouter, Depends

from app.config import Settings, get_settings

router = APIRouter(prefix="/api/config", tags=["Configuration"])


@router.get("", summary="Lấy cấu hình cơ bản của ứng dụng")
async def get_app_config(
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """
    Trả về cấu hình hiển thị công khai (tên app, mô tả, giới hạn ký tự,...)
    giúp giao diện tự động điều chỉnh mà không bị hardcode tên thương hiệu.
    """
    return {
        "app_name": settings.app_name,
        "app_description": settings.app_description,
        "max_text_length": settings.max_text_length,
        "chunk_size": settings.chunk_size,
        "default_voice": settings.default_voice,
    }
