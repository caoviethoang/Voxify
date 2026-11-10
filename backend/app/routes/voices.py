import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.dependencies import get_tts_service
from app.models.admin import SystemVoiceSetting
from app.services.tts_service import TTSService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voices", tags=["Voices"])


@router.get("", summary="Lấy danh sách các giọng đọc khả dụng")
async def get_voices(
    refresh: bool = Query(False, description="Bắt buộc làm mới danh sách từ provider"),
    tts_service: TTSService = Depends(get_tts_service),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Trả về danh sách giọng đọc được phân loại:
    - ID, tên hiển thị, giới tính, ngôn ngữ/locale
    - Giọng đọc tiếng Việt (vi-VN) được sắp xếp ưu tiên ở đầu danh sách
    - Áp dụng cấu hình ghi đè từ bảng SystemVoiceSetting (bật/tắt, nhãn, hệ số nhân)
    """
    try:
        raw_voices = await tts_service.get_voices(force_refresh=refresh)

        # Lấy overrides từ DB
        settings_res = await db.execute(select(SystemVoiceSetting))
        settings_map = {s.voice_id: s for s in settings_res.scalars().all()}

        active_voices: List[Dict[str, Any]] = []
        for v in raw_voices:
            vid = v.get("id", "")
            cfg = settings_map.get(vid)
            if cfg and not cfg.is_active:
                continue  # Bỏ qua giọng đã bị admin tắt toàn hệ thống

            merged = dict(v)
            if cfg:
                if cfg.name:
                    merged["name"] = cfg.name
                merged["tier"] = cfg.tier
                merged["credit_multiplier"] = cfg.credit_multiplier
            else:
                merged["tier"] = "free"
                merged["credit_multiplier"] = 1.0

            active_voices.append(merged)

        vietnamese_voices = [v for v in active_voices if v.get("is_vietnamese")]

        return {
            "total": len(active_voices),
            "vietnamese_count": len(vietnamese_voices),
            "voices": active_voices,
        }
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách giọng đọc: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Không thể tải danh sách giọng đọc lúc này: {str(e)}",
        )
