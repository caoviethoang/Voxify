"""Giao diện trừu tượng cho nhà cung cấp Clone giọng nói (CloneProvider)."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class CloneProvider(ABC):
    """
    Interface định nghĩa các thao tác clone giọng:
    - clone_voice: Đăng ký mẫu âm thanh và huấn luyện/tạo profile giọng
    - delete_cloned_voice: Xóa giọng clone trên engine
    - synthesize: Tổng hợp giọng nói từ profile clone
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Tên định danh provider (ví dụ: 'mock', 'elevenlabs', 'xtts', 'f5tts')."""
        pass

    @abstractmethod
    async def clone_voice(
        self,
        name: str,
        audio_file_path: str,
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Tạo profile clone từ tệp âm thanh mẫu (5–30s).

        Trả về dict:
        - provider_voice_id: str
        - metadata: dict
        """
        pass

    @abstractmethod
    async def delete_cloned_voice(self, provider_voice_id: str) -> bool:
        """Xóa profile giọng clone khỏi provider."""
        pass

    @abstractmethod
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
        """
        Tổng hợp văn bản thành âm thanh nhị phân (MP3) bằng giọng đã clone.
        """
        pass
