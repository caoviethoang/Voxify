from functools import lru_cache
from app.config import get_settings
from app.providers import get_provider
from app.services.tts_service import TTSService

_tts_service_instance: TTSService | None = None


def get_tts_service() -> TTSService:
    """Trả về thể hiện singleton của TTSService dùng chung trong toàn bộ app."""
    global _tts_service_instance
    if _tts_service_instance is None:
        settings = get_settings()
        # Mặc định sử dụng edge-tts, có thể mở rộng chọn provider qua cấu hình .env
        provider = get_provider("edge")
        _tts_service_instance = TTSService(provider=provider, settings=settings)
    return _tts_service_instance
