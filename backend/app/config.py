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

    # Frontend URL cho reset password & verify email links
    frontend_url: str = "http://localhost:5173"

    # Bảo mật & JWT
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # Xác thực email (bật/tắt)
    require_email_verification: bool = False

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # Email SMTP / Resend (dev in ra console nếu thiếu host)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    emails_from: str = "noreply@voxify.app"

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

    # Hệ thống Credit
    credit_chars_per_credit: int = 1  # 1 ký tự = 1 credit mặc định
    credit_signup_bonus: int = 10000  # Tặng credit khi đăng ký
    credit_provider_multipliers: dict[str, float] = {
        "edge": 1.0,
        "azure": 1.2,
        "elevenlabs": 2.0,
    }

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, v: Any) -> bool:
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "debug", "dev")
        return bool(v)

    @field_validator("require_email_verification", mode="before")
    @classmethod
    def parse_require_email(cls, v: Any) -> bool:
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes")
        return bool(v)

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
