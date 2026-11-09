"""Factory tạo đối tượng CloneProvider phù hợp cấu hình hệ thống."""
from typing import Optional

from app.config import Settings, get_settings
from app.providers.clone_base import CloneProvider
from app.providers.clone_elevenlabs import ElevenLabsCloneProvider
from app.providers.clone_mock import MockCloneProvider
from app.providers.clone_xtts import XTTSCloneProvider

_cached_clone_provider: Optional[CloneProvider] = None


def get_clone_provider(settings: Optional[Settings] = None) -> CloneProvider:
    """Trả về Singleton CloneProvider theo cấu hình."""
    global _cached_clone_provider
    if _cached_clone_provider is not None:
        return _cached_clone_provider

    s = settings or get_settings()
    provider_name = getattr(s, "clone_provider", "mock").lower()

    if provider_name == "elevenlabs":
        _cached_clone_provider = ElevenLabsCloneProvider()
    elif provider_name in ("xtts", "f5tts"):
        _cached_clone_provider = XTTSCloneProvider()
    else:
        _cached_clone_provider = MockCloneProvider()

    return _cached_clone_provider
