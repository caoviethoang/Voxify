"""Model lưu trữ thông tin và tiến trình các tác vụ lồng tiếng phụ đề (DubbingJob)."""
from typing import Optional

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TimestampMixin


class DubbingJob(Base, TimestampMixin):
    """Bảng quản lý công việc lồng tiếng phụ đề (Subtitle Dubbing - Issue #21)."""
    __tablename__ = "dubbing_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Khóa ngoại người dùng sở hữu tác vụ
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Tiêu đề tác vụ (tên file hoặc tên do người dùng đặt)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Lồng tiếng phụ đề")

    # Định dạng phụ đề đầu vào ("srt" | "vtt") và định dạng audio đầu ra ("mp3" | "wav")
    subtitle_format: Mapped[str] = mapped_column(String(10), default="srt", nullable=False)
    target_format: Mapped[str] = mapped_column(String(10), default="mp3", nullable=False)

    # Giọng đọc mặc định
    default_voice: Mapped[str] = mapped_column(String(100), default="vi-VN-HoaiMyNeural", nullable=False)

    # Trạng thái tiến trình: queued | processing | done | failed
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Số lượng cue và ký tự
    total_cues: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    credit_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Dữ liệu kịch bản các cue (dạng JSON string: start, end, duration, text, voice, actual_duration, tempo, warning, audio_url)
    cues_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Đường dẫn file âm thanh master hoàn chỉnh và file zip các cue
    output_audio_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    output_zip_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Hòa âm nền & Audio Ducking (tùy chọn)
    background_audio_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    ducking_volume: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)

    # Thông báo lỗi nếu thất bại và tổng thời lượng âm thanh hoàn chỉnh
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Quan hệ người dùng
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id])  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_dubbing_jobs_user_status", "user_id", "status"),
    )
