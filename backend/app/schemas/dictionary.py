"""Schemas cho Từ điển phát âm cá nhân (Pronunciation Dictionary)."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class DictionaryRuleCreateRequest(BaseModel):
    word: str = Field(..., min_length=1, max_length=150, description="Từ gốc cần thay thế")
    replacement: str = Field(..., min_length=1, max_length=255, description="Cách đọc / phiên âm thay thế")
    category: Optional[str] = Field(default="custom", description="Phân loại: abbreviation, date, number, name, custom")


class DictionaryRuleUpdateRequest(BaseModel):
    replacement: Optional[str] = Field(default=None, min_length=1, max_length=255)
    category: Optional[str] = None
    is_active: Optional[bool] = None


class DictionaryRuleResponse(BaseModel):
    id: int
    user_id: int
    word: str
    replacement: str
    category: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
