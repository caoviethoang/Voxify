"""Schemas Pydantic cho Quản lý API Key & Public API v1 (Issue #13)."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# ----------------------------------------------------------------------
# Quản lý API Key (Dashboard / Frontend)
# ----------------------------------------------------------------------

class ApiKeyCreateRequest(BaseModel):
    """Yêu cầu tạo API Key mới."""
    name: str = Field(..., min_length=1, max_length=100, description="Tên gợi nhớ cho API Key")


class ApiKeyCreatedResponse(BaseModel):
    """
    Phản hồi khi tạo API Key thành công.
    LƯU Ý: raw_key chỉ hiển thị duy nhất 1 lần tại thời điểm tạo.
    """
    id: int
    name: str
    key_prefix: str
    raw_key: str
    created_at: datetime


class ApiKeyItemResponse(BaseModel):
    """Thông tin API Key trong danh sách (không bao giờ lộ raw_key hay hash)."""
    id: int
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None


class ApiStatsDailyItem(BaseModel):
    date: str
    requests: int
    credits: int


class ApiStatsResponse(BaseModel):
    """Thống kê lượng request và credit tiêu thụ qua API."""
    total_requests: int
    total_credits: int
    daily_usage: List[ApiStatsDailyItem]


# ----------------------------------------------------------------------
# Public API v1 (/v1/...)
# ----------------------------------------------------------------------

class V1TTSRequest(BaseModel):
    """Yêu cầu tổng hợp giọng nói qua Public API v1."""
    text: str = Field(..., min_length=1, max_length=50000, description="Nội dung văn bản cần đọc")
    voice: str = Field("vi-VN-HoaiMyNeural", description="ID giọng đọc (hệ thống hoặc clone_...)")
    rate: str = Field("+0%", description="Tốc độ: -50% đến +100%")
    pitch: str = Field("+0Hz", description="Cao độ: -50Hz đến +50Hz")
    volume: str = Field("+0%", description="Âm lượng: -50% đến +50%")
    mode: str = Field("sync", description="Chế độ: 'sync' (chờ kết quả) hoặc 'async' (xử lý nền)")
    webhook_url: Optional[str] = Field(None, description="URL nhận thông báo khi job async hoàn thành")


class V1TTSResponse(BaseModel):
    """Kết quả tạo giọng nói qua Public API v1."""
    job_id: Optional[int] = None
    status: str = Field(..., description="'completed' | 'processing'")
    audio_url: Optional[str] = None
    duration: Optional[float] = None
    credits_used: int
    message: Optional[str] = None


class V1JobResponse(BaseModel):
    """Trạng thái tiến trình của Job TTS."""
    id: int
    status: str
    progress: int
    audio_url: Optional[str] = None
    duration: float
    credits_used: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class V1CreditsResponse(BaseModel):
    """Thông tin số dư credit và hạn mức rate limit của API Key."""
    credit_balance: int
    plan_tier: str
    rate_limit_per_minute: int
    user_email: str
