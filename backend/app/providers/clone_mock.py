"""Mock CloneProvider phục vụ phát triển cục bộ và kiểm thử tự động không cần GPU/API ngoại vi."""
import logging
import uuid
from typing import Any, Dict, Optional

from app.providers.clone_base import CloneProvider
from app.providers.fake import FakeTTSProvider

logger = logging.getLogger(__name__)


class MockCloneProvider(CloneProvider):
    """
    Mock Provider cho Voice Cloning:
    - Lưu danh sách voice trong bộ nhớ
    - Tổng hợp audio giả lập hoặc ủy quyền engine TTS nội bộ
    - Luôn hoạt động offline cho unit test và CI
    """

    def __init__(self, fallback_tts: Optional[Any] = None):
        self._voices: Dict[str, Dict[str, Any]] = {}
        self._fallback_tts = fallback_tts or FakeTTSProvider()

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
        return await self._fallback_tts.synthesize(
            text=text,
            voice=provider_voice_id,
            rate=rate,
            pitch=pitch,
            volume=volume,
        )
