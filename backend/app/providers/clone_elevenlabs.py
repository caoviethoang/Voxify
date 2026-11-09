"""ElevenLabs Instant Voice Clone Provider."""
import logging
import os
from typing import Any, Dict, Optional

import httpx

from app.config import get_settings
from app.providers.clone_base import CloneProvider
from app.providers.clone_mock import MockCloneProvider

logger = logging.getLogger(__name__)


class ElevenLabsCloneProvider(CloneProvider):
    """
    Tích hợp dịch vụ ElevenLabs Instant Voice Clone API:
    - POST https://api.elevenlabs.io/v1/voices/add
    - DELETE https://api.elevenlabs.io/v1/voices/{voice_id}
    - POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
    """

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or getattr(settings, "elevenlabs_api_key", "")
        self.base_url = "https://api.elevenlabs.io/v1"
        self._mock_fallback = MockCloneProvider()

    @property
    def provider_name(self) -> str:
        return "elevenlabs"

    async def clone_voice(
        self,
        name: str,
        audio_file_path: str,
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if not self.api_key:
            logger.warning("ElevenLabs API Key chưa được thiết lập, chuyển sang chế độ Mock.")
            return await self._mock_fallback.clone_voice(name, audio_file_path, description, **kwargs)

        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Không tìm thấy tệp mẫu âm thanh: {audio_file_path}")

        headers = {
            "xi-api-key": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(audio_file_path, "rb") as f:
                    files = {
                        "files": (os.path.basename(audio_file_path), f, "audio/mpeg"),
                    }
                    data = {
                        "name": name,
                        "description": description or f"Cloned voice for {name}",
                    }
                    res = await client.post(f"{self.base_url}/voices/add", headers=headers, data=data, files=files)
                    if res.status_code in (401, 403, 500, 502, 503):
                        logger.warning(f"ElevenLabs trả về mã {res.status_code}, fallback sang mock clone.")
                        return await self._mock_fallback.clone_voice(name, audio_file_path, description, **kwargs)
                    if res.status_code >= 400:
                        logger.error(f"ElevenLabs clone voice thất bại: {res.status_code} {res.text}")
                        raise ValueError(f"Lỗi từ ElevenLabs API: {res.text}")

                    res_data = res.json()
                    voice_id = res_data.get("voice_id")
                    return {
                        "provider_voice_id": voice_id,
                        "metadata": res_data,
                    }
        except httpx.RequestError as exc:
            logger.warning(f"Lỗi kết nối tới ElevenLabs API ({exc}), sử dụng mock fallback.")
            return await self._mock_fallback.clone_voice(name, audio_file_path, description, **kwargs)

    async def delete_cloned_voice(self, provider_voice_id: str) -> bool:
        if not self.api_key or provider_voice_id.startswith("mock_"):
            return await self._mock_fallback.delete_cloned_voice(provider_voice_id)

        headers = {"xi-api-key": self.api_key}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.delete(f"{self.base_url}/voices/{provider_voice_id}", headers=headers)
                return res.status_code in (200, 204, 404)
        except httpx.RequestError:
            return await self._mock_fallback.delete_cloned_voice(provider_voice_id)

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
        if not self.api_key or provider_voice_id.startswith("mock_"):
            return await self._mock_fallback.synthesize(
                text=text,
                provider_voice_id=provider_voice_id,
                audio_sample_path=audio_sample_path,
                rate=rate,
                pitch=pitch,
                volume=volume,
                **kwargs,
            )

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(
                    f"{self.base_url}/text-to-speech/{provider_voice_id}",
                    headers=headers,
                    json=payload,
                )
                if res.status_code in (401, 403, 500, 502, 503):
                    logger.warning(f"ElevenLabs synthesize trả về mã {res.status_code}, fallback mock.")
                    return await self._mock_fallback.synthesize(
                        text=text,
                        provider_voice_id=provider_voice_id,
                        audio_sample_path=audio_sample_path,
                        rate=rate,
                        pitch=pitch,
                        volume=volume,
                        **kwargs,
                    )
                if res.status_code >= 400:
                    logger.error(f"ElevenLabs synthesize thất bại: {res.status_code} {res.text}")
                    raise ValueError(f"Không thể tổng hợp giọng clone qua ElevenLabs: {res.text}")
                return res.content
        except httpx.RequestError as exc:
            logger.warning(f"Lỗi kết nối tới ElevenLabs TTS ({exc}), sử dụng mock fallback.")
            return await self._mock_fallback.synthesize(
                text=text,
                provider_voice_id=provider_voice_id,
                audio_sample_path=audio_sample_path,
                rate=rate,
                pitch=pitch,
                volume=volume,
                **kwargs,
            )
