"""S3Storage — Lưu trữ file audio trên AWS S3 hoặc Cloudflare R2."""
import asyncio
import logging
from typing import Any, Optional

from app.config import get_settings
from app.storage import StorageBackend

logger = logging.getLogger(__name__)

boto3: Any = None
BaseClient: Any = Any
Config: Any = None
ClientError: Any = Exception

try:
    import boto3 as _boto3
    from botocore.client import BaseClient as _BaseClient
    from botocore.config import Config as _Config
    from botocore.exceptions import ClientError as _ClientError
    boto3 = _boto3
    BaseClient = _BaseClient
    Config = _Config
    ClientError = _ClientError
except ImportError:
    pass


class S3Storage(StorageBackend):
    """
    Adapter lưu trữ tương thích S3 API (hỗ trợ cả AWS S3 và Cloudflare R2).
    Hỗ trợ presigned URL có thời hạn và CDN public URL.
    """

    def __init__(self, client: Optional[Any] = None) -> None:
        self.settings = get_settings()
        self.bucket = self.settings.s3_bucket_name or "voxify"
        self.endpoint_url = self.settings.s3_endpoint_url or None
        self.region_name = self.settings.s3_region_name or "auto"
        self.public_cdn_url = (self.settings.s3_public_cdn_url or "").rstrip("/")
        self.presigned_expiry = self.settings.s3_presigned_expiry_seconds or 3600
        self._client = client

    def _get_client(self) -> Any:
        """Khởi tạo S3 client nếu chưa có."""
        if self._client is not None:
            return self._client

        if boto3 is None:
            raise RuntimeError(
                "Thư viện boto3 chưa được cài đặt. Vui lòng cài đặt boto3 để sử dụng S3Storage."
            )

        config = Config(signature_version="s3v4") if Config else None
        self._client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.settings.s3_access_key_id,
            aws_secret_access_key=self.settings.s3_secret_access_key,
            region_name=self.region_name,
            config=config,
        )
        return self._client

    async def save(self, data: bytes, filename: str) -> str:
        """
        Tải bytes lên S3/R2 và trả về object key (path).
        """
        # Xác định Content-Type
        content_type = "audio/mpeg"
        if filename.endswith(".wav"):
            content_type = "audio/wav"
        elif filename.endswith(".ogg"):
            content_type = "audio/ogg"
        elif filename.endswith(".json"):
            content_type = "application/json"
        elif filename.endswith(".vtt"):
            content_type = "text/vtt"
        elif filename.endswith(".srt"):
            content_type = "text/plain"

        # Chuẩn hóa object key
        key = filename.lstrip("/")

        def _upload() -> None:
            client = self._get_client()
            client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )

        await asyncio.to_thread(_upload)
        logger.info(f"Đã tải file lên S3/R2: bucket={self.bucket}, key={key} ({len(data)} bytes)")
        return key

    async def get_url(self, path: str) -> str:
        """
        Trả về URL công khai (nếu có CDN) hoặc Presigned URL có thời hạn.
        """
        key = path.lstrip("/")

        # Nếu có cấu hình CDN công khai, trả về link trực tiếp qua CDN
        if self.public_cdn_url:
            return f"{self.public_cdn_url}/{key}"

        # Mặc định tạo Presigned GET URL có hạn sử dụng
        def _generate_presigned_url() -> str:
            client = self._get_client()
            url: str = client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=self.presigned_expiry,
            )
            return url

        return await asyncio.to_thread(_generate_presigned_url)

    async def delete(self, path: str) -> None:
        """Xóa file khỏi S3/R2."""
        key = path.lstrip("/")

        def _delete() -> None:
            client = self._get_client()
            client.delete_object(Bucket=self.bucket, Key=key)

        try:
            await asyncio.to_thread(_delete)
            logger.info(f"Đã xóa file khỏi S3/R2: bucket={self.bucket}, key={key}")
        except Exception as e:
            logger.warning(f"Lỗi khi xóa file {key} trên S3: {e}")

    async def get_presigned_upload_url(
        self,
        filename: str,
        content_type: str = "audio/mpeg",
        expires_in: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Tạo presigned PUT URL cho phép client frontend trực tiếp upload file lên R2/S3.
        """
        key = filename.lstrip("/")
        expiry = expires_in or self.presigned_expiry

        def _generate_put_url() -> str:
            client = self._get_client()
            url: str = client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expiry,
            )
            return url

        upload_url = await asyncio.to_thread(_generate_put_url)
        return {
            "upload_url": upload_url,
            "key": key,
            "bucket": self.bucket,
            "expires_in": expiry,
        }
