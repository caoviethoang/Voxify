import asyncio
import logging
import re
from typing import Any, Dict, List

import edge_tts

from app.providers.base import TTSProvider

logger = logging.getLogger(__name__)

# Ngưỡng ký tự tối đa cho mỗi lần gọi edge-tts.
# Microsoft silently closes WebSocket cho văn bản dài / nhiều dấu Unicode tiếng Việt (đặc biệt giọng HoaiMy).
# Giữ nhỏ (~80 ký tự) để chia theo dấu phẩy/mệnh đề tự nhiên và tránh bị Microsoft từ chối NoAudioReceived.
_MICRO_CHUNK_MAX = 80


class EdgeTTSProvider(TTSProvider):
    """
    Hiện thực TTSProvider sử dụng thư viện edge-tts (dịch vụ giọng nói Microsoft Edge).

    Workaround quan trọng: Microsoft Edge TTS đóng WebSocket không gửi audio khi
    text quá dài hoặc chứa nhiều ký tự Unicode tiếng Việt trong một lần gọi.
    Giải pháp: tách text thành micro-chunk ≤ _MICRO_CHUNK_MAX ký tự tại tầng provider,
    gọi riêng từng chunk rồi nối MP3 bytes lại.
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
                # Rút gọn tên hiển thị: loại bỏ tiền tố Microsoft và đuôi Online (Natural)
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

        Tự động tách thành micro-chunk nhỏ để tránh lỗi NoAudioReceived
        khi Microsoft từ chối văn bản tiếng Việt dài.
        """
        if not text.strip():
            raise ValueError("Văn bản chuyển đổi không được để trống.")

        formatted_rate = self._format_percent(rate, default="+0%")
        formatted_volume = self._format_percent(volume, default="+0%")
        formatted_pitch = self._format_hz(pitch, default="+0Hz")

        # Tách text thành các đoạn nhỏ ở tầng provider
        chunks = _split_into_micro_chunks(text)
        logger.debug(f"Tách văn bản thành {len(chunks)} micro-chunk để gọi edge-tts")

        all_audio: List[bytes] = []
        for i, chunk in enumerate(chunks):
            chunk_audio = await self._synthesize_chunk(
                chunk=chunk,
                voice=voice,
                rate=formatted_rate,
                pitch=formatted_pitch,
                volume=formatted_volume,
                chunk_index=i + 1,
                total=len(chunks),
            )
            all_audio.append(chunk_audio)
            # Delay an toàn giữa các request tránh rate-limit / connection drops của Microsoft Bing
            if i < len(chunks) - 1:
                await asyncio.sleep(0.25)

        return b"".join(all_audio)

    async def _synthesize_chunk(
        self,
        chunk: str,
        voice: str,
        rate: str,
        pitch: str,
        volume: str,
        chunk_index: int,
        total: int,
        max_retries: int = 3,
    ) -> bytes:
        """Tổng hợp giọng nói cho một đoạn văn bản nhỏ, có retry và fallback dự phòng."""
        last_exception: Exception | None = None
        target_voice = voice

        for attempt in range(1, max_retries + 1):
            try:
                current_chunk = chunk
                # Nếu gặp lỗi ở lần thử đầu, chuẩn hóa dấu câu và thử giọng fallback tương thích
                if attempt >= 2:
                    current_chunk = re.sub(r'[!¡]+', '.', current_chunk)
                    if voice == "vi-VN-HoaiMyNeural":
                        target_voice = "vi-VN-NamMinhNeural"
                    elif voice == "vi-VN-NamMinhNeural":
                        target_voice = "vi-VN-HoaiMyNeural"

                communicate = edge_tts.Communicate(
                    text=current_chunk,
                    voice=target_voice,
                    rate=rate,
                    pitch=pitch,
                    volume=volume,
                )

                audio_chunks: List[bytes] = []
                async for segment in communicate.stream():
                    if segment.get("type") == "audio":
                        audio_chunks.append(segment["data"])

                if not audio_chunks:
                    raise RuntimeError("Không nhận được dữ liệu âm thanh từ dịch vụ.")

                logger.debug(
                    f"Chunk {chunk_index}/{total} OK (voice: {target_voice}): {len(b''.join(audio_chunks))} bytes"
                )
                return b"".join(audio_chunks)

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Chunk {chunk_index}/{total} (voice: {target_voice}) – thử {attempt}/{max_retries} thất bại: {e}"
                )
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * attempt)  # back-off tuyến tính

        raise RuntimeError(
            f"Lỗi kết nối khi tạo giọng nói (chunk {chunk_index}/{total}). "
            f"Vui lòng kiểm tra kết nối mạng hoặc thử lại: {last_exception}"
        ) from last_exception

    # ------------------------------------------------------------------
    # Helpers định dạng tham số
    # ------------------------------------------------------------------

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


# ------------------------------------------------------------------
# Hàm tách micro-chunk (module-level để dễ test)
# ------------------------------------------------------------------

# Thứ tự ưu tiên tách: câu > mệnh đề > dấu phẩy > khoảng trắng
_SENTENCE_ENDINGS = re.compile(r'(?<=[.!?…])\s+')
_CLAUSE_ENDINGS = re.compile(r'(?<=[;:])\s+')
_COMMA_ENDINGS = re.compile(r'(?<=,)\s+')


def _split_into_micro_chunks(text: str, max_len: int = _MICRO_CHUNK_MAX) -> List[str]:
    """
    Tách văn bản thành các đoạn nhỏ ≤ max_len ký tự.

    Ưu tiên tách tại:
    1. Dấu kết thúc câu (. ! ? …)
    2. Dấu chấm phẩy / hai chấm (; :)
    3. Dấu phẩy (,)
    4. Khoảng trắng bất kỳ (word boundary)
    5. Cắt cứng nếu không có khoảng trắng

    Bỏ qua các đoạn rỗng sau khi strip.
    """
    text = text.strip()
    if not text:
        return []

    if len(text) <= max_len:
        return [text]

    # Thử tách theo câu trước
    result = _recursive_split(text, max_len)
    return [c for c in result if c.strip()]


def _recursive_split(text: str, max_len: int) -> List[str]:
    """Tách đệ quy: thử từng mức dấu câu, cuối cùng là word boundary."""
    if len(text) <= max_len:
        return [text]

    # Thử từng pattern theo thứ tự ưu tiên
    for pattern in (_SENTENCE_ENDINGS, _CLAUSE_ENDINGS, _COMMA_ENDINGS):
        parts = pattern.split(text)
        if len(parts) > 1:
            return _merge_or_split_parts(parts, max_len)

    # Tách tại khoảng trắng
    words = text.split(" ")
    if len(words) > 1:
        return _merge_or_split_parts(words, max_len, joiner=" ")

    # Cắt cứng (từ đơn rất dài – hiếm gặp)
    return [text[i:i + max_len] for i in range(0, len(text), max_len)]


def _merge_or_split_parts(
    parts: List[str],
    max_len: int,
    joiner: str = " ",
) -> List[str]:
    """
    Gộp các phần nhỏ lại với nhau miễn là tổng độ dài ≤ max_len,
    nếu một phần vẫn vượt max_len thì đệ quy tách tiếp.
    """
    result: List[str] = []
    buffer = ""

    for part in parts:
        part = part.strip()
        if not part:
            continue

        candidate = f"{buffer}{joiner}{part}".strip() if buffer else part

        if len(candidate) <= max_len:
            buffer = candidate
        else:
            if buffer:
                result.append(buffer)
            # Nếu phần đơn lẻ vẫn vượt ngưỡng, tách tiếp
            if len(part) > max_len:
                result.extend(_recursive_split(part, max_len))
                buffer = ""
            else:
                buffer = part

    if buffer:
        result.append(buffer)

    return result
