"""Pydantic schemas cho Dashboard API."""
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.schemas.history import HistoryItemResponse


class DashboardStatsResponse(BaseModel):
    chars_used_this_month: int
    total_audio_generated: int
    total_duration_seconds: float
    credit_balance: int
    latest_generation: Optional[HistoryItemResponse] = None
    recent_activities: List[HistoryItemResponse] = []

    model_config = ConfigDict(from_attributes=True)

