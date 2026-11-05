from abc import ABC, abstractmethod
from typing import Any, Dict, List


class TTSProvider(ABC):
    """
    Interface định nghĩa trừu tượng cho các nhà cung cấp TTS (Edge-TTS, Azure, ElevenLabs, Vbee,...).
    Giúp tầng dịch vụ và route độc lập hoàn toàn với engine cụ thể.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Tên định danh của provider (ví dụ: 'edge', 'azure', 'elevenlabs')."""
        pass

    @abstractmethod
    async def list_voices(self) -> List[Dict[str, Any]]:
        """
        Lấy danh sách giọng đọc khả dụng.

        Trả về danh sách dict chuẩn hóa với các trường tối thiểu:
        - id: str (mã định danh giọng đọc)
        - name: str (tên hiển thị thân thiện)
        - gender: str (giới tính: Female, Male, Neutral)
        - locale: str (mã ngôn ngữ/vùng: vi-VN, en-US,...)
        - locale_name: str (tên ngôn ngữ hiển thị)
        """
        pass

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%",
    ) -> bytes:
        """
        Tổng hợp văn bản thành tệp âm thanh nhị phân (mặc định định dạng MP3).

        Tham số:
        - text: Văn bản cần đọc
        - voice: ID giọng đọc
        - rate: Tốc độ đọc (ví dụ: '+0%', '+20%', '-10%')
        - pitch: Cao độ giọng (ví dụ: '+0Hz', '+10Hz', '-5Hz')
        - volume: Âm lượng (ví dụ: '+0%', '-10%')

        Trả về:
        - bytes: Dữ liệu âm thanh MP3
        """
        pass
