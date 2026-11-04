"""Cấu hình ứng dụng — đọc từ biến môi trường hoặc file .env."""
from functools import lru_cache
from pathlib import Path
from typing import Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Thông tin ứng dụng
    app_name: str = "Voxify"
    app_description: str = "Nền tảng chuyển đổi văn bản thành giọng nói"

    # Máy chủ
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, v: Any) -> bool:
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "debug", "dev")
        return bool(v)

    # Bảo mật
    secret_key: str = "change-me-in-production"

    # Database (SQLite mặc định khi dev, PostgreSQL khi prod)
    database_url: str = "sqlite+aiosqlite:///./storage/db.sqlite"

    # Redis (tùy chọn, dùng cho hàng đợi Phase 2+)
    redis_url: str = "redis://localhost:6379/0"

    # Lưu trữ file audio
    storage_path: str = "./storage/audio"
    storage_backend: str = "local"  # "local" | "s3"

    # TTS engine
    tts_provider: str = "edge"  # "edge" | "azure" | "elevenlabs"
    default_voice: str = "vi-VN-HoaiMyNeural"

    # Giới hạn xử lý
    max_chars: int = 20000
    chunk_size: int = 2500

    # Legacy aliases để tương thích với code cũ
    @property
    def max_text_length(self) -> int:
        return self.max_chars

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Singleton cấu hình ứng dụng."""
    return Settings()
