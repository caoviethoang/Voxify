"""Pydantic schemas cho TTS API."""
from typing import Optional
from pydantic import BaseModel, Field


class TTSRequest(BaseModel):
    """Yêu cầu tổng hợp giọng nói."""
    text: str = Field(..., min_length=1, description="Văn bản cần đọc")
    voice: str = Field(..., min_length=1, description="Mã giọng đọc")
    rate: Optional[str] = Field(default="+0%", description="Tốc độ nói")
    pitch: Optional[str] = Field(default="+0Hz", description="Cao độ")
    volume: Optional[str] = Field(default="+0%", description="Âm lượng")
    preview: Optional[bool] = Field(default=False, description="Chỉ đọc 200 ký tự đầu")


class TTSResponse(BaseModel):
    """Phản hồi metadata sau khi tạo giọng nói (nếu cần trả JSON)."""
    generation_id: int
    char_count: int
    file_size: int
    voice: str
    is_preview: bool
