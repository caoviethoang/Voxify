"""Pydantic schemas cho Voice Library (Issue #18)."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class VoiceLibraryItem(BaseModel):
    """Schema đầy đủ cho một mục trong Voice Library."""
    id: int
    owner_id: Optional[int] = None
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    provider: str
    provider_voice_id: Optional[str] = None
    voice_type: str  # system | cloned | imported
    language: str
    gender: str
    tags: Optional[str] = None
    preview_url: Optional[str] = None
    sample_duration: Optional[float] = None
    visibility: str
    status: str
    is_active: bool
    tier: str
    credit_multiplier: float
    cloned_voice_ref: Optional[str] = None
    total_uses: int
    created_at: datetime
    is_favorite: bool = False

    model_config = {"from_attributes": True}


class VoiceLibraryListResponse(BaseModel):
    """Danh sách Voice Library với metadata."""
    total: int
    voices: List[VoiceLibraryItem]
    favorite_ids: List[int]


class ToggleFavoriteResponse(BaseModel):
    """Phản hồi khi thêm/xoá yêu thích."""
    voice_id: int
    is_favorite: bool
    message: str


class SyncVoicesResponse(BaseModel):
    """Phản hồi khi admin đồng bộ giọng."""
    synced: int
    message: str


class VoiceUpdateRequest(BaseModel):
    """Admin: cập nhật cấu hình giọng (bật/tắt, tier, multiplier)."""
    is_active: Optional[bool] = None
    tier: Optional[str] = None
    credit_multiplier: Optional[float] = None
    tags: Optional[str] = None
    display_name: Optional[str] = None
