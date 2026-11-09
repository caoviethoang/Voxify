"""Mock CloneProvider phục vụ phát triển cục bộ và kiểm thử tự động không cần GPU/API ngoại vi."""
import logging
import uuid
from typing import Any, Dict, Optional

from app.config import get_settings
from app.providers.clone_base import CloneProvider
from app.providers.fake import FakeTTSProvider

logger = logging.getLogger(__name__)


class MockCloneProvider(CloneProvider):
    """
    Mock Provider cho Voice Cloning:
    - Lưu danh sách voice trong bộ nhớ.
    - Trong môi trường thực tế (development/production):
      Ủy quyền sang EdgeTTSProvider (với giọng tương ứng theo giới tính Nam/Nữ và ngôn ngữ)
      để người dùng nhận được âm thanh tiếng Việt thực sự hoàn chỉnh, đầy đủ nội dung văn bản.
    - Trong môi trường testing/offline hoặc khi không có mạng:
      Tự động dự phòng an toàn sang FakeTTSProvider.
    """

    def __init__(self, fallback_tts: Optional[Any] = None):
        self._voices: Dict[str, Dict[str, Any]] = {}
        self._fallback_tts = fallback_tts

    @property
    def provider_name(self) -> str:
        return "mock"

    async def clone_voice(
        self,
        name: str,
        audio_file_path: str,
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        provider_voice_id = f"mock_{uuid.uuid4().hex[:12]}"
        meta = {
            "name": name,
            "description": description,
            "audio_file_path": audio_file_path,
            "status": "ready",
            "provider": "mock",
            "gender": kwargs.get("gender", "unspecified"),
            "language": kwargs.get("language", "vi-VN"),
        }
        self._voices[provider_voice_id] = meta
        logger.info(f"MockCloneProvider: Đã tạo voice clone '{name}' ({provider_voice_id})")
        return {
            "provider_voice_id": provider_voice_id,
            "metadata": meta,
        }

    async def delete_cloned_voice(self, provider_voice_id: str) -> bool:
        if provider_voice_id in self._voices:
            del self._voices[provider_voice_id]
            logger.info(f"MockCloneProvider: Đã xóa voice {provider_voice_id}")
            return True
        return True

    async def synthesize(
        self,
        text: str,
        provider_voice_id: str,
        audio_sample_path: Optional[str] = None,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%",
        **kwargs: Any,
    ) -> bytes:
        logger.info(f"MockCloneProvider: Đang tổng hợp {len(text)} ký tự với voice {provider_voice_id}")

        # 1. Nếu có fallback_tts được chỉ định tường minh (ví dụ unit test mock)
        if self._fallback_tts is not None:
            return await self._fallback_tts.synthesize(
                text=text,
                voice=provider_voice_id,
                rate=rate,
                pitch=pitch,
                volume=volume,
            )

        # 2. Kiểm tra nếu đang chạy test environment / offline provider fake
        settings = get_settings()
        is_testing = (
            getattr(settings, "environment", "").lower() == "testing"
            or getattr(settings, "tts_provider", "").lower() == "fake"
        )
        if is_testing:
            fake = FakeTTSProvider()
            return await fake.synthesize(
                text=text,
                voice=provider_voice_id,
                rate=rate,
                pitch=pitch,
                volume=volume,
            )

        # 3. Môi trường thực tế: Chọn giọng EdgeTTS phù hợp theo giới tính & ngôn ngữ
        gender = kwargs.get("gender") or self._voices.get(provider_voice_id, {}).get("gender", "unspecified")
        language = kwargs.get("language") or self._voices.get(provider_voice_id, {}).get("language", "vi-VN")

        if "en" in str(language).lower():
            edge_voice = "en-US-GuyNeural" if gender == "male" else "en-US-JennyNeural"
        else:
            edge_voice = "vi-VN-NamMinhNeural" if gender == "male" else "vi-VN-HoaiMyNeural"

        try:
            from app.providers.edge import EdgeTTSProvider

            edge_provider = EdgeTTSProvider()
            return await edge_provider.synthesize(
                text=text,
                voice=edge_voice,
                rate=rate,
                pitch=pitch,
                volume=volume,
            )
        except Exception as exc:
            logger.warning(
                f"MockCloneProvider: EdgeTTS không khả dụng ({exc}), dự phòng tạo âm thanh offline."
            )
            fake = FakeTTSProvider()
            return await fake.synthesize(
                text=text,
                voice=provider_voice_id,
                rate=rate,
                pitch=pitch,
                volume=volume,
            )
