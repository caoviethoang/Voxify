"""Pydantic schemas cho TTS API và Background Jobs."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TTSRequest(BaseModel):
    """Yêu cầu tổng hợp giọng nói đồng bộ / nghe thử."""
    text: str = Field(..., min_length=1, description="Văn bản cần đọc")
    voice: str = Field(..., min_length=1, description="Mã giọng đọc")
    rate: Optional[str] = Field(default="+0%", description="Tốc độ nói")
    pitch: Optional[str] = Field(default="+0Hz", description="Cao độ")
    volume: Optional[str] = Field(default="+0%", description="Âm lượng")
    preview: Optional[bool] = Field(default=False, description="Chỉ đọc 200 ký tự đầu")


class TTSJobCreateRequest(BaseModel):
    """Yêu cầu tạo job bất đồng bộ."""
    text: str = Field(..., min_length=1, description="Văn bản cần đọc (hỗ trợ văn bản dài)")
    voice: str = Field(..., min_length=1, description="Mã giọng đọc")
    rate: Optional[str] = Field(default="+0%", description="Tốc độ nói")
    pitch: Optional[str] = Field(default="+0Hz", description="Cao độ")
    volume: Optional[str] = Field(default="+0%", description="Âm lượng")
    format: Optional[str] = Field(default="mp3", description="Định dạng âm thanh: mp3 hoặc wav")
    apply_dictionary: Optional[bool] = Field(default=True, description="Áp dụng từ điển phát âm cá nhân")


class TTSJobResponse(BaseModel):
    """Phản hồi thông tin và tiến độ của Job."""
    id: int
    status: str
    progress: int
    text: str = ""
    char_count: int
    duration: float
    format: str
    credit_used: int
    voice: str
    error_message: Optional[str] = None
    audio_url: Optional[str] = None
    srt_url: Optional[str] = None
    vtt_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TTSResponse(BaseModel):
    """Phản hồi metadata sau khi tạo giọng nói."""
    generation_id: int
    char_count: int
    file_size: int
    voice: str
    is_preview: bool
