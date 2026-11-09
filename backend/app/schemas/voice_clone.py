"""Pydantic schemas cho tính năng Clone giọng nói."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ClonedVoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    voice_id: str
    user_id: int
    name: str
    description: Optional[str] = None
    sample_duration: float
    sample_size_bytes: int
    quality_score: Optional[float] = None
    gender: str = "unspecified"
    language: str = "vi-VN"
    provider: str
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    preview_url: Optional[str] = None
    sample_url: Optional[str] = None


class VoiceCloneQuota(BaseModel):
    used: int
    max_allowed: int
    plan_name: str
    creation_fee: int
    multiplier: float


class ClonedVoiceListResponse(BaseModel):
    total: int
    quota: VoiceCloneQuota
    voices: List[ClonedVoiceResponse]


class VoiceCloneUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class VoiceAbuseReportCreateRequest(BaseModel):
    reason: str = Field(..., description="celebrity_impersonation | no_consent | copyright | defamation | other")
    description: str = Field(..., min_length=10, max_length=2000)
    reporter_email: Optional[str] = None


class VoiceAbuseReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cloned_voice_id: int
    reason: str
    description: str
    status: str
    created_at: datetime
