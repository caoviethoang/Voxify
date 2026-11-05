"""Pydantic schemas cho danh sách giọng đọc."""
from typing import Optional

from pydantic import BaseModel


class VoiceSchema(BaseModel):
    """Thông tin một giọng đọc."""
    id: str
    name: str
    full_name: Optional[str] = None
    gender: str
    locale: str
    locale_name: Optional[str] = None
    is_vietnamese: bool = False
    suggested_codec: Optional[str] = None


class VoiceListResponse(BaseModel):
    """Danh sách giọng đọc với metadata."""
    voices: list[VoiceSchema]
    total: int
    vietnamese_count: int
