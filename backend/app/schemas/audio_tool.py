"""Pydantic schemas cho Khung Công cụ Âm thanh (Audio Tools Framework) — Issue #20."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AudioToolCost(BaseModel):
    type: str  # "free" | "per_minute" | "fixed"
    rate: Optional[int] = 0


class AudioToolResponse(BaseModel):
    id: str
    name_vi: str
    name_en: str
    description_vi: str
    description_en: str
    category: str
    category_name_vi: str
    category_name_en: str
    icon: str
    params_schema: Dict[str, Any]
    cost: Dict[str, Any]
    heavy: bool


class AudioToolCategoryGroup(BaseModel):
    category: str
    name_vi: str
    name_en: str
    icon: str
    tools: List[AudioToolResponse]


class AudioToolListResponse(BaseModel):
    total: int
    tools: List[AudioToolResponse]
    categories: Dict[str, AudioToolCategoryGroup]


class AudioToolJobResponse(BaseModel):
    id: int
    tool_id: str
    user_id: int
    status: str
    progress: int
    input_filename: str
    input_duration: Optional[float] = None
    params: Optional[Dict[str, Any]] = None
    output_filename: Optional[str] = None
    output_duration: Optional[float] = None
    output_size_bytes: Optional[int] = None
    output_url: Optional[str] = None
    stream_url: Optional[str] = None
    credit_used: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AudioToolJobListResponse(BaseModel):
    total: int
    jobs: List[AudioToolJobResponse]
