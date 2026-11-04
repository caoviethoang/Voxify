import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_tts_service
from app.services.tts_service import TTSService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voices", tags=["Voices"])


@router.get("", summary="Lấy danh sách các giọng đọc khả dụng")
async def get_voices(
    refresh: bool = Query(False, description="Bắt buộc làm mới danh sách từ provider"),
    tts_service: TTSService = Depends(get_tts_service),
) -> Dict[str, Any]:
    """
    Trả về danh sách giọng đọc được phân loại:
    - ID, tên hiển thị, giới tính, ngôn ngữ/locale
    - Giọng đọc tiếng Việt (vi-VN) được sắp xếp ưu tiên ở đầu danh sách
    - Có cơ chế cache trong bộ nhớ để phản hồi nhanh
    """
    try:
        voices = await tts_service.get_voices(force_refresh=refresh)
        vietnamese_voices = [v for v in voices if v.get("is_vietnamese")]

        return {
            "total": len(voices),
            "vietnamese_count": len(vietnamese_voices),
            "voices": voices,
        }
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách giọng đọc: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Không thể tải danh sách giọng đọc lúc này: {str(e)}",
        )
