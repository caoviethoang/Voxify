"""Cấu hình ứng dụng — đọc từ biến môi trường hoặc file .env."""
from functools import lru_cache
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
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    max_upload_size_mb: int = 25
    max_concurrent_jobs_free: int = 2
    max_concurrent_jobs_pro: int = 5
    max_concurrent_jobs_vip: int = 10
    max_concurrent_jobs_admin: int = 20

    # Kiểm duyệt nội dung & Chống lạm dụng (Issue #16)
    moderation_enabled: bool = True
    moderation_max_violations_before_ban: int = 3

    # Giám sát & Quan sát (Observability - Issue #16)
    log_format: str = "text"  # "text" | "json"
    sentry_dsn: str = ""

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
        "clone": 1.5,
    }

    # Clone giọng nói (Voice Cloning)
    clone_provider: str = "mock"  # "mock" | "elevenlabs" | "xtts" | "f5tts"
    elevenlabs_api_key: str = ""
    xtts_api_url: str = ""
    f5tts_api_url: str = ""
    clone_creation_fee: int = 500  # Phí tạo 1 voice clone (credits)
    clone_voice_multiplier: float = 1.5  # Hệ số nhân credit khi đọc bằng giọng clone
    clone_storage_path: str = "./storage/clones"
    clone_sample_min_duration: float = 5.0  # Thời lượng mẫu âm thanh tối thiểu (giây)
    clone_sample_max_duration: float = 180.0  # Thời lượng mẫu âm thanh tối đa (3 phút = 180 giây)
    max_cloned_voices_free: int = 1
    max_cloned_voices_pro: int = 5
    max_cloned_voices_vip: int = 20

    # Cổng thanh toán & VietQR
    vietqr_bank_id: str = "MB"  # Mã ngân hàng (MB, VCB, TCB, ACB, ...)
    vietqr_account_no: str = "0333888999"
    vietqr_account_name: str = "VOXIFY AI STUDIO"
    vietqr_template: str = "compact2"

    # PayOS (Cổng thanh toán tự động VietQR)
    payos_client_id: str = ""
    payos_api_key: str = ""
    payos_checksum_key: str = ""

    # Stripe (Thanh toán quốc tế)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

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


@lru_cache
def get_settings() -> Settings:
    """Singleton cấu hình ứng dụng."""
    return Settings()
