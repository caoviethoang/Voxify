"""Pydantic schemas cho History API."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class HistoryItemResponse(BaseModel):
    id: int
    title: str  # 60 ký tự đầu của text, hoặc tiêu đề tùy chỉnh
    text: str
    voice: str
    rate: str
    pitch: str
    volume: str
    format: str
    duration: float
    char_count: int
    credit_used: int
    status: str
    progress: int
    error_message: Optional[str] = None
    audio_url: Optional[str] = None
    srt_url: Optional[str] = None
    vtt_url: Optional[str] = None
    is_preview: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class HistoryListResponse(BaseModel):
    items: List[HistoryItemResponse]
    total: int
    page: int
    limit: int
    pages: int


class BulkDeleteRequest(BaseModel):
    ids: List[int]


class UpdateHistoryTitleRequest(BaseModel):
    title: str
