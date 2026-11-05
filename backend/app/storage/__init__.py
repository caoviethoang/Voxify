"""StorageBackend interface và factory."""
from abc import ABC, abstractmethod

from app.storage.local import LocalStorage


class StorageBackend(ABC):
    """Interface lưu trữ file audio."""

    @abstractmethod
    async def save(self, data: bytes, filename: str) -> str:
        """Lưu file, trả về đường dẫn."""
        ...

    @abstractmethod
    async def get_url(self, path: str) -> str:
        """Trả về URL công khai của file."""
        ...

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Xóa file."""
        ...


def get_storage(backend: str = "local") -> StorageBackend:
    """Factory tạo storage backend theo cấu hình."""
    if backend == "local":
        return LocalStorage()  # type: ignore[return-value]
    raise ValueError(f"Storage backend '{backend}' chưa được hỗ trợ.")
