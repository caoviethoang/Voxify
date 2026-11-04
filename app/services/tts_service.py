import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.config import Settings, get_settings
from app.providers.base import TTSProvider
from app.services.text_splitter import split_text_into_chunks

logger = logging.getLogger(__name__)


class TTSService:
    """
    Tầng nghiệp vụ (Service layer) quản lý việc tổng hợp âm thanh và danh sách giọng đọc.
    Đảm nhiệm:
    - Cache danh sách giọng đọc trong bộ nhớ
    - Sắp xếp ưu tiên giọng tiếng Việt lên đầu
    - Kiểm tra giới hạn độ dài ký tự (tối đa 20.000 ký tự)
    - Xử lý văn bản dài: cắt theo câu thành các đoạn (~2.500 ký tự) và ghép lại
    - Hỗ trợ chế độ nghe thử 200 ký tự đầu
    """

    def __init__(self, provider: TTSProvider, settings: Optional[Settings] = None):
        self.provider = provider
        self.settings = settings or get_settings()
        self._cached_voices: Optional[List[Dict[str, Any]]] = None
        self._cache_lock = asyncio.Lock()

    async def get_voices(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Lấy danh sách giọng đọc có cache trong bộ nhớ.
        Sắp xếp các giọng tiếng Việt (vi-VN) lên đầu bảng để tiện sử dụng.
        """
        async with self._cache_lock:
            if self._cached_voices is not None and not force_refresh:
                return self._cached_voices

            logger.info("Đang nạp danh sách giọng đọc từ engine...")
            raw_voices = await self.provider.list_voices()

            # Phân tách giọng tiếng Việt và các giọng quốc tế khác
            vi_voices: List[Dict[str, Any]] = []
            other_voices: List[Dict[str, Any]] = []

            for v in raw_voices:
                locale = v.get("locale", "").lower()
                if locale.startswith("vi") or "vietnam" in v.get("locale_name", "").lower():
                    v["is_vietnamese"] = True
                    vi_voices.append(v)
                else:
                    v["is_vietnamese"] = False
                    other_voices.append(v)

            # Sắp xếp tên tiếng Việt
            vi_voices.sort(key=lambda x: x.get("name", ""))
            # Sắp xếp ngôn ngữ khác theo locale rồi tên
            other_voices.sort(key=lambda x: (x.get("locale", ""), x.get("name", "")))

            # Ghép danh sách: Tiếng Việt ở vị trí ưu tiên đầu tiên
            sorted_voices = vi_voices + other_voices
            self._cached_voices = sorted_voices
            logger.info(
                f"Đã nạp {len(sorted_voices)} giọng đọc ({len(vi_voices)} giọng tiếng Việt)."
            )
            return sorted_voices

    async def synthesize(
        self,
        text: str,
        voice: str,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%",
        preview: bool = False,
    ) -> bytes:
        """
        Tổng hợp giọng nói cho đoạn văn bản.
        - Giới hạn tối đa: 20.000 ký tự (báo lỗi tiếng Việt nếu vượt).
        - Nghe thử: chỉ lấy 200 ký tự đầu.
        - Text dài (> 2.500 ký tự): cắt thành các câu nhỏ rồi tổng hợp và ghép nối.
        """
        raw_text = text.strip() if text else ""
        if not raw_text:
            raise ValueError("Vui lòng nhập nội dung văn bản cần chuyển thành giọng nói.")

        # Xử lý chế độ nghe thử (preview)
        if preview:
            processing_text = raw_text[:200]
            logger.info(f"Đang tổng hợp nghe thử ({len(processing_text)} ký tự)...")
        else:
            # Kiểm tra giới hạn 20.000 ký tự theo yêu cầu
            if len(raw_text) > self.settings.max_text_length:
                raise ValueError(
                    f"Văn bản vượt quá giới hạn cho phép {self.settings.max_text_length:,} ký tự. "
                    f"Hiện tại văn bản có {len(raw_text):,} ký tự. Vui lòng rút ngắn nội dung."
                )
            processing_text = raw_text

        # Xác thực giọng đọc hợp lệ nếu có cache
        await self._validate_voice(voice)

        # Kiểm tra độ dài xem có cần cắt đoạn không
        chunk_size = self.settings.chunk_size
        if len(processing_text) <= chunk_size:
            # Xử lý trực tiếp 1 đoạn
            return await self.provider.synthesize(
                text=processing_text,
                voice=voice,
                rate=rate,
                pitch=pitch,
                volume=volume,
            )

        # Xử lý văn bản dài: cắt theo câu (~2.500 ký tự/đoạn)
        chunks = split_text_into_chunks(processing_text, max_chunk_size=chunk_size)
        logger.info(
            f"Văn bản dài {len(processing_text)} ký tự được chia thành {len(chunks)} đoạn để xử lý."
        )

        audio_parts: List[bytes] = []
        for index, chunk in enumerate(chunks, start=1):
            logger.debug(f"Đang tổng hợp đoạn {index}/{len(chunks)} ({len(chunk)} ký tự)...")
            part_audio = await self.provider.synthesize(
                text=chunk,
                voice=voice,
                rate=rate,
                pitch=pitch,
                volume=volume,
            )
            audio_parts.append(part_audio)

        # Ghép các đoạn âm thanh MP3 lại với nhau
        combined_audio = b"".join(audio_parts)
        logger.info(
            f"Hoàn thành ghép nối {len(audio_parts)} đoạn âm thanh. Kích thước: {len(combined_audio)} bytes."
        )
        return combined_audio

    async def _validate_voice(self, voice_id: str) -> None:
        """Kiểm tra giọng đọc có tồn tại trong danh sách không."""
        try:
            voices = await self.get_voices()
            voice_ids = {v["id"] for v in voices}
            if voice_id not in voice_ids:
                logger.warning(f"Giọng đọc '{voice_id}' không có trong danh sách khả dụng.")
                # Nếu không tìm thấy, kiểm tra xem có phải định dạng edge-tts không
                if not voice_id.startswith(("vi-", "en-", "zh-", "ja-", "ko-", "fr-", "de-")):
                    raise ValueError(f"Giọng đọc '{voice_id}' không tồn tại hoặc không hợp lệ.")
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            logger.warning(f"Bỏ qua bước xác thực giọng đọc vì không thể tải danh sách: {e}")
