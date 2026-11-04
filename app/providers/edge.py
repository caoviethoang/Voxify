import asyncio
import logging
from typing import Any, Dict, List
import edge_tts

from app.providers.base import TTSProvider

logger = logging.getLogger(__name__)


class EdgeTTSProvider(TTSProvider):
    """
    Hiện thực TTSProvider sử dụng thư viện edge-tts (dịch vụ giọng nói Microsoft Edge).
    """

    @property
    def provider_name(self) -> str:
        return "edge-tts"

    async def list_voices(self) -> List[Dict[str, Any]]:
        """Lấy danh sách các giọng đọc từ edge-tts và chuẩn hóa dữ liệu."""
        try:
            raw_voices = await edge_tts.list_voices()
            standardized: List[Dict[str, Any]] = []

            for v in raw_voices:
                short_name = v.get("ShortName", "")
                friendly_name = v.get("FriendlyName", "")
                # Rút gọn tên hiển thị cho trực quan: loại bỏ tiền tố Microsoft và đuôi Online (Natural)
                display_name = (
                    friendly_name.replace("Microsoft ", "")
                    .replace(" Online (Natural)", "")
                    .strip()
                )
                if not display_name:
                    display_name = short_name

                standardized.append({
                    "id": short_name,
                    "name": display_name,
                    "full_name": friendly_name,
                    "gender": v.get("Gender", "Unknown"),
                    "locale": v.get("Locale", "unknown"),
                    "locale_name": v.get("LocaleName", ""),
                    "suggested_codec": v.get("SuggestedCodec", "audio-24khz-48kbitrate-mono-mp3"),
                })

            return standardized
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách giọng đọc từ edge-tts: {e}")
            raise RuntimeError(f"Không thể tải danh sách giọng đọc: {str(e)}") from e

    async def synthesize(
        self,
        text: str,
        voice: str,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%",
    ) -> bytes:
        """
        Chuyển đổi văn bản thành âm thanh MP3 thông qua edge-tts.
        Có cơ chế thử lại ngắn phòng trường hợp kết nối gián đoạn.
        """
        if not text.strip():
            raise ValueError("Văn bản chuyển đổi không được để trống.")

        # Định dạng tham số hợp lệ cho edge-tts nếu truyền dạng số
        formatted_rate = self._format_percent(rate, default="+0%")
        formatted_volume = self._format_percent(volume, default="+0%")
        formatted_pitch = self._format_hz(pitch, default="+0Hz")

        max_retries = 2
        last_exception = None

        for attempt in range(1, max_retries + 1):
            try:
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=voice,
                    rate=formatted_rate,
                    pitch=formatted_pitch,
                    volume=formatted_volume,
                )

                audio_chunks: List[bytes] = []
                async for chunk in communicate.stream():
                    if chunk.get("type") == "audio":
                        audio_chunks.append(chunk["data"])

                if not audio_chunks:
                    raise RuntimeError("Không nhận được dữ liệu âm thanh từ dịch vụ TTS.")

                return b"".join(audio_chunks)

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Thử nghiệm {attempt}/{max_retries} tổng hợp giọng nói thất bại: {e}"
                )
                if attempt < max_retries:
                    await asyncio.sleep(0.5)

        raise RuntimeError(
            f"Lỗi kết nối khi tạo giọng nói. Vui lòng kiểm tra kết nối mạng hoặc thử lại: {last_exception}"
        ) from last_exception

    @staticmethod
    def _format_percent(val: str, default: str = "+0%") -> str:
        """Chuẩn hóa giá trị phần trăm (ví dụ: '10' -> '+10%', '-5%' -> '-5%')."""
        if not val:
            return default
        val = str(val).strip()
        if not val.endswith("%"):
            try:
                num = int(float(val))
                return f"{'+' if num >= 0 else ''}{num}%"
            except ValueError:
                return default
        # Đã có %, kiểm tra dấu
        if not val.startswith(("+", "-")):
            return f"+{val}"
        return val

    @staticmethod
    def _format_hz(val: str, default: str = "+0Hz") -> str:
        """Chuẩn hóa giá trị tần số Hz (ví dụ: '10' -> '+10Hz', '-5Hz' -> '-5Hz')."""
        if not val:
            return default
        val = str(val).strip()
        if not val.lower().endswith("hz"):
            try:
                num = int(float(val))
                return f"{'+' if num >= 0 else ''}{num}Hz"
            except ValueError:
                return default
        if not val.startswith(("+", "-")):
            return f"+{val}"
        return val
