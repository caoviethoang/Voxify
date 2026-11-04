from typing import Dict, Type
from app.providers.base import TTSProvider
from app.providers.edge import EdgeTTSProvider

_PROVIDERS: Dict[str, Type[TTSProvider]] = {
    "edge": EdgeTTSProvider,
    "edge-tts": EdgeTTSProvider,
}


def get_provider(name: str = "edge") -> TTSProvider:
    """
    Factory tạo thể hiện TTSProvider theo tên cấu hình.
    Dễ dàng mở rộng cho Azure / ElevenLabs / Vbee sau này.
    """
    provider_cls = _PROVIDERS.get(name.lower())
    if not provider_cls:
        raise ValueError(
            f"Provider '{name}' không được hỗ trợ. Các provider hiện có: {list(_PROVIDERS.keys())}"
        )
    return provider_cls()


__all__ = ["TTSProvider", "EdgeTTSProvider", "get_provider"]
