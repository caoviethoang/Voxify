"""Service lưu trữ file audio — wrap StorageBackend."""
import logging
from datetime import UTC, datetime

from app.config import get_settings
from app.storage import StorageBackend, get_storage

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
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
        prefix = "preview" if is_preview else "speech"
        clean_voice = voice.replace("/", "_").replace("\\", "_")
        filename = f"{prefix}_{clean_voice}_{timestamp}.mp3"

        path = await self.backend.save(data, filename)
        logger.info(f"Đã lưu audio: {path} ({len(data)} bytes)")
        return path, len(data)

    async def get_url(self, path: str) -> str:
        """Lấy URL công khai của file audio."""
        return await self.backend.get_url(path)

    async def delete(self, path: str) -> None:
        """Xóa file audio khỏi storage."""
        await self.backend.delete(path)

    def cleanup_old_local_files(self, days: int = 30) -> int:
        """
        Dọn dẹp các file audio và file tạm cũ hơn số ngày quy định trên local storage.
        Trả về số lượng file đã được dọn dẹp.
        """
        import time
        from pathlib import Path

        settings = get_settings()
        storage_path = Path(settings.storage_path)
        temp_path = Path("storage/temp")
        deleted_count = 0
        cutoff_time = time.time() - (days * 86400)

        for target_dir in (storage_path, temp_path):
            if not target_dir.exists():
                continue
            for file_path in target_dir.rglob("*"):
                if file_path.is_file():
                    try:
                        if file_path.stat().st_mtime < cutoff_time:
                            file_path.unlink()
                            deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Không thể xóa file cũ {file_path}: {e}")

        logger.info(f"Đã dọn dẹp {deleted_count} file cũ (> {days} ngày)")
        return deleted_count
