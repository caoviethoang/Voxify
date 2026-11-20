"""Schemas Pydantic cho chức năng Lồng tiếng phụ đề (Issue #21)."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SubtitleCueItem(BaseModel):
    """Mỗi đoạn phụ đề (cue) sau khi phân tích và cấu hình lồng tiếng."""
    index: int
    start: float = Field(..., ge=0.0, description="Thời điểm bắt đầu (giây)")
    end: float = Field(..., ge=0.0, description="Thời điểm kết thúc (giây)")
    duration: float = Field(..., ge=0.0, description="Thời lượng cho phép của câu (giây)")
    text: str = Field(..., min_length=1, description="Nội dung phụ đề")
    voice: str = Field(..., description="ID giọng đọc áp dụng cho cue này")
    original_voice_tag: Optional[str] = Field(None, description="Tên giọng được chỉ định trong cú pháp [Voice: ...]")
    char_count: int = Field(0, description="Số lượng ký tự")
    actual_duration: Optional[float] = Field(default=None, description="Thời lượng audio TTS thực tế (giây)")
    adjusted_tempo: Optional[float] = Field(default=None, description="Hệ số tempo đã co/dãn (tối đa 1.35x)")
    warning: Optional[str] = Field(default=None, description="Cảnh báo vượt ngưỡng thời lượng cho phép")
    audio_url: Optional[str] = Field(default=None, description="Đường dẫn nghe thử file âm thanh của cue này")


class DubbingParseRequest(BaseModel):
    """Yêu cầu phân tích cú pháp nội dung file phụ đề SRT/VTT."""
    content: str = Field(..., min_length=1, description="Toàn bộ nội dung thô của file phụ đề")
    default_voice: str = Field("vi-VN-HoaiMyNeural", description="Giọng đọc mặc định gán cho các cue")


class DubbingParseResponse(BaseModel):
    """Kết quả phân tích phụ đề trả về cho giao diện Studio."""
    cues: List[SubtitleCueItem]
    total_cues: int
    char_count: int
    estimated_credits: int
    warnings_count: int = 0


class DubbingPreviewCueRequest(BaseModel):
    """Nghe thử 1 câu phụ đề trước khi render toàn bộ."""
    text: str = Field(..., min_length=1, description="Nội dung câu cần nghe thử")
    voice: str = Field("vi-VN-HoaiMyNeural", description="Giọng đọc")
    target_duration: Optional[float] = Field(None, description="Thời lượng mục tiêu của câu (giây) để test tempo sync")


class DubbingCreateJobRequest(BaseModel):
    """Yêu cầu bắt đầu tác vụ tổng hợp lồng tiếng phụ đề."""
    title: str = Field("Lồng tiếng phụ đề", max_length=255)
    subtitle_format: str = Field("srt", pattern="^(srt|vtt)$")
    target_format: str = Field("mp3", pattern="^(mp3|wav)$")
    default_voice: str = Field("vi-VN-HoaiMyNeural", max_length=100)
    cues: List[SubtitleCueItem]
    ducking_volume: float = Field(0.2, ge=0.0, le=1.0, description="Âm lượng nhạc nền khi có giọng nói (0.0 - 1.0)")
    background_audio_path: Optional[str] = Field(None, description="Đường dẫn file nhạc nền trên server")


class DubbingJobResponse(BaseModel):
    """Chi tiết trạng thái tác vụ lồng tiếng."""
    id: int
    user_id: int
    title: str
    subtitle_format: str
    target_format: str
    default_voice: str
    status: str
    progress: int
    total_cues: int
    char_count: int
    credit_used: int
    cues_data: Optional[str] = None
    output_audio_path: Optional[str] = None
    output_zip_path: Optional[str] = None
    background_audio_path: Optional[str] = None
    ducking_volume: float
    error_message: Optional[str] = None
    duration: float
    created_at: datetime
    updated_at: datetime
    audio_download_url: Optional[str] = None
    zip_download_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
