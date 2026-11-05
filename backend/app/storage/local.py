"""LocalStorage — lưu file audio vào thư mục storage trên máy chủ."""
import logging
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)


class LocalStorage:
    """Lưu trữ file trên filesystem cục bộ."""

    def __init__(self) -> None:
        settings = get_settings()
        self.base_path = Path(settings.storage_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(self, data: bytes, filename: str) -> str:
        """Lưu bytes vào file, trả về đường dẫn tương đối."""
        file_path = self.base_path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)
        logger.debug(f"Đã lưu file: {file_path} ({len(data)} bytes)")
        return str(file_path)

    async def get_url(self, path: str) -> str:
        """Trả về URL tương đối (backend phục vụ qua /storage/...)."""
        return f"/storage/{Path(path).name}"

    async def delete(self, path: str) -> None:
        """Xóa file nếu tồn tại."""
        file_path = Path(path)
        if file_path.exists():
            file_path.unlink()
            logger.debug(f"Đã xóa file: {file_path}")
