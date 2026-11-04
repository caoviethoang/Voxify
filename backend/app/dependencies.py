"""FastAPI dependencies — singleton instances."""
from functools import lru_cache

from app.config import get_settings
from app.providers import ProviderRegistry
from app.services.tts_service import TTSService


@lru_cache()
def get_tts_service() -> TTSService:
    """Singleton TTSService với provider được cấu hình từ .env."""
    settings = get_settings()
    provider = ProviderRegistry.get(settings.tts_provider)
    return TTSService(provider=provider, settings=settings)
