"""Tự host XTTS-v2 / F5-TTS Clone Provider."""
import logging
import os
import uuid
from typing import Any, Dict, Optional

import httpx

from app.config import get_settings
from app.providers.clone_base import CloneProvider
from app.providers.clone_mock import MockCloneProvider

logger = logging.getLogger(__name__)


class XTTSCloneProvider(CloneProvider):
    """
    Tích hợp XTTS-v2 / F5-TTS tự host (Self-hosted model server qua HTTP API).
    """

    def __init__(self, api_url: Optional[str] = None):
        settings = get_settings()
        self.api_url = api_url or getattr(settings, "xtts_api_url", "")
        self._mock_fallback = MockCloneProvider()

    @property
    def provider_name(self) -> str:
        return "xtts"

    async def clone_voice(
        self,
        name: str,
        audio_file_path: str,
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if not self.api_url:
            logger.info("XTTS URL chưa thiết lập, sử dụng Mock Clone Provider.")
            return await self._mock_fallback.clone_voice(name, audio_file_path, description, **kwargs)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(audio_file_path, "rb") as f:
                    files = {"audio_file": (os.path.basename(audio_file_path), f, "audio/wav")}
                    data = {"speaker_name": name}
                    res = await client.post(f"{self.api_url}/api/clone", data=data, files=files)
                    if res.status_code >= 400:
                        raise ValueError(f"XTTS API error: {res.text}")
                    data_res = res.json()
                    return {
                        "provider_voice_id": data_res.get("speaker_id", f"xtts_{uuid.uuid4().hex[:8]}"),
                        "metadata": data_res,
                    }
        except httpx.RequestError as exc:
            logger.warning(f"Lỗi kết nối tới XTTS server ({exc}), fallback mock.")
            return await self._mock_fallback.clone_voice(name, audio_file_path, description, **kwargs)

    async def delete_cloned_voice(self, provider_voice_id: str) -> bool:
        if not self.api_url or provider_voice_id.startswith("mock_"):
            return await self._mock_fallback.delete_cloned_voice(provider_voice_id)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.delete(f"{self.api_url}/api/speakers/{provider_voice_id}")
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
        if not self.api_url or provider_voice_id.startswith("mock_"):
            return await self._mock_fallback.synthesize(
                text=text,
                provider_voice_id=provider_voice_id,
                audio_sample_path=audio_sample_path,
                rate=rate,
                pitch=pitch,
                volume=volume,
                **kwargs,
            )

        payload = {
            "text": text,
            "speaker_id": provider_voice_id,
            "language": kwargs.get("language", "vi"),
            "speaker_wav": audio_sample_path,
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(f"{self.api_url}/api/tts", json=payload)
                if res.status_code >= 400:
                    raise ValueError(f"XTTS tổng hợp thất bại: {res.text}")
                return res.content
        except httpx.RequestError as exc:
            logger.warning(f"Lỗi kết nối tới XTTS server ({exc}), fallback mock.")
            return await self._mock_fallback.synthesize(
                text=text,
                provider_voice_id=provider_voice_id,
                audio_sample_path=audio_sample_path,
                rate=rate,
                pitch=pitch,
                volume=volume,
                **kwargs,
            )
