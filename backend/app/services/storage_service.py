"""Service lưu trữ file audio — wrap StorageBackend."""
import logging
from datetime import datetime, timezone

from app.storage import get_storage, StorageBackend
from app.config import get_settings

logger = logging.getLogger(__name__)


class StorageService:
    """Dịch vụ lưu và quản lý file audio."""

    def __init__(self, backend: StorageBackend | None = None) -> None:
        settings = get_settings()
        self.backend = backend or get_storage(settings.storage_backend)

    async def save_audio(self, data: bytes, voice: str, is_preview: bool = False) -> tuple[str, int]:
        """
        Lưu file audio. Trả về (đường dẫn, kích thước bytes).
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        prefix = "preview" if is_preview else "speech"
        clean_voice = voice.replace("/", "_").replace("\\", "_")
        filename = f"{prefix}_{clean_voice}_{timestamp}.mp3"

        path = await self.backend.save(data, filename)
        logger.info(f"Đã lưu audio: {path} ({len(data)} bytes)")
        return path, len(data)

    async def get_url(self, path: str) -> str:
        """Lấy URL công khai của file audio."""
        return await self.backend.get_url(path)
