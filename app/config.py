import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cấu hình ứng dụng nạp từ biến môi trường hoặc file .env."""

    app_name: str = "Voxify"
    app_description: str = "Nền tảng chuyển đổi văn bản thành giọng nói"
    host: str = "0.0.0.0"
    port: int = 8000
    max_text_length: int = 20000
    chunk_size: int = 2500
    default_voice: str = "vi-VN-HoaiMyNeural"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Hàm singleton trả về cấu hình ứng dụng được cache."""
    return Settings()
