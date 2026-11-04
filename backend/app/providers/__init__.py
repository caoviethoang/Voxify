"""ProviderRegistry — chọn TTS provider theo tên từ cấu hình."""
from app.providers.base import TTSProvider
from app.providers.edge import EdgeTTSProvider


class ProviderRegistry:
    """Registry quản lý các TTS provider được đăng ký."""

    _providers: dict[str, type[TTSProvider]] = {
        "edge": EdgeTTSProvider,
    }

    @classmethod
    def register(cls, name: str, provider_class: type[TTSProvider]) -> None:
        """Đăng ký thêm provider mới (Azure, ElevenLabs, Vbee...)."""
        cls._providers[name] = provider_class

    @classmethod
    def get(cls, name: str) -> TTSProvider:
        """Lấy instance provider theo tên. Raise nếu không tồn tại."""
        provider_class = cls._providers.get(name)
        if provider_class is None:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Provider '{name}' không tồn tại. Provider khả dụng: {available}"
            )
        return provider_class()

    @classmethod
    def available(cls) -> list[str]:
        """Danh sách tên provider đã đăng ký."""
        return list(cls._providers.keys())
