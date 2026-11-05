"""FakeTTSProvider — Giả lập engine TTS cho môi trường test và CI/CD không cần mạng ngoài."""
import asyncio
from typing import Any, Dict, List

from app.providers.base import TTSProvider


class FakeTTSProvider(TTSProvider):
    """
    Provider giả lập hoàn toàn ngoại tuyến:
    - Không gọi bất kỳ dịch vụ đám mây nào (Edge, Azure, ElevenLabs...).
    - Trả về dữ liệu âm thanh MP3 hợp lệ.
    - Hỗ trợ giả lập độ trễ (latency) và lỗi (error) để kiểm thử hoàn credit, retry.
    """

    def __init__(
        self,
        simulate_error: bool = False,
        error_message: str = "Fake TTS provider simulation error",
        latency: float = 0.0,
    ):
        self.simulate_error = simulate_error
        self.error_message = error_message
        self.latency = latency
        self.synthesize_call_count = 0
        self.last_synthesized_text = ""
        self.last_synthesized_voice = ""

    @property
    def provider_name(self) -> str:
        return "fake"

    async def list_voices(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "vi-VN-HoaiMyNeural",
                "name": "HoaiMy - Vietnamese (Vietnam)",
                "gender": "Female",
                "locale": "vi-VN",
                "locale_name": "Vietnamese (Vietnam)",
                "suggested_codec": "audio/mpeg",
                "is_vietnamese": True,
            },
            {
                "id": "vi-VN-NamMinhNeural",
                "name": "NamMinh - Vietnamese (Vietnam)",
                "gender": "Male",
                "locale": "vi-VN",
                "locale_name": "Vietnamese (Vietnam)",
                "suggested_codec": "audio/mpeg",
                "is_vietnamese": True,
            },
            {
                "id": "en-US-JennyNeural",
                "name": "Jenny - English (United States)",
                "gender": "Female",
                "locale": "en-US",
                "locale_name": "English (United States)",
                "suggested_codec": "audio/mpeg",
                "is_vietnamese": False,
            },
        ]

    async def synthesize(
        self,
        text: str,
        voice: str,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%",
    ) -> bytes:
        self.synthesize_call_count += 1
        self.last_synthesized_text = text
        self.last_synthesized_voice = voice

        if self.latency > 0:
            await asyncio.sleep(self.latency)

        if self.simulate_error:
            raise RuntimeError(self.error_message)

        # Trả về chuỗi frame MP3 giả lập hợp lệ
        num_frames = max(2, min(50, len(text) // 10 + 1))
        single_frame = b"\xff\xfb\x90\x64" + (b"\x00" * 414)
        return single_frame * num_frames

