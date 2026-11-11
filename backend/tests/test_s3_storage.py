"""Tests cho Cloudflare R2 / AWS S3 Storage Adapter và Storage Service Retention."""
from unittest.mock import MagicMock, patch

import pytest

from app.services.storage_service import StorageService
from app.storage import get_storage
from app.storage.s3 import S3Storage


@pytest.mark.asyncio
async def test_s3_storage_save_and_url_with_cdn():
    mock_boto_client = MagicMock()
    mock_boto_client.put_object.return_value = {}
    mock_boto_client.generate_presigned_url.return_value = "https://mock-s3.com/test.mp3?sig=123"

    with patch("app.storage.s3.get_settings") as mock_settings:
        mock_settings.return_value.s3_bucket_name = "test-bucket"
        mock_settings.return_value.s3_endpoint_url = "https://r2.example.com"
        mock_settings.return_value.s3_region_name = "auto"
        mock_settings.return_value.s3_access_key_id = "test-key"
        mock_settings.return_value.s3_secret_access_key = "test-secret"
        mock_settings.return_value.s3_public_cdn_url = "https://cdn.example.com"
        mock_settings.return_value.s3_presigned_expiry_seconds = 1800

        storage = S3Storage(client=mock_boto_client)

        # 1. Test save
        data = b"ID3\x03\x00\x00\x00fake-audio-content"
        filename = "speech_test.mp3"
        saved_key = await storage.save(data, filename)

        assert saved_key == "speech_test.mp3"
        mock_boto_client.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="speech_test.mp3",
            Body=data,
            ContentType="audio/mpeg",
        )

        # 2. Test get_url with public CDN
        url = await storage.get_url(saved_key)
        assert url == "https://cdn.example.com/speech_test.mp3"


@pytest.mark.asyncio
async def test_s3_storage_presigned_url_without_cdn():
    mock_boto_client = MagicMock()
    mock_boto_client.generate_presigned_url.return_value = "https://r2.example.com/bucket/private.wav?sig=abc"

    with patch("app.storage.s3.get_settings") as mock_settings:
        mock_settings.return_value.s3_bucket_name = "private-bucket"
        mock_settings.return_value.s3_endpoint_url = "https://r2.example.com"
        mock_settings.return_value.s3_region_name = "auto"
        mock_settings.return_value.s3_access_key_id = "test-key"
        mock_settings.return_value.s3_secret_access_key = "test-secret"
        mock_settings.return_value.s3_public_cdn_url = ""
        mock_settings.return_value.s3_presigned_expiry_seconds = 7200

        storage = S3Storage(client=mock_boto_client)

        url = await storage.get_url("private.wav")
        assert "private.wav" in url
        mock_boto_client.generate_presigned_url.assert_called_once_with(
            ClientMethod="get_object",
            Params={"Bucket": "private-bucket", "Key": "private.wav"},
            ExpiresIn=7200,
        )


@pytest.mark.asyncio
async def test_s3_storage_delete_and_presigned_upload():
    mock_boto_client = MagicMock()
    mock_boto_client.delete_object.return_value = {}
    mock_boto_client.generate_presigned_url.return_value = "https://r2.example.com/upload-signed-url"

    with patch("app.storage.s3.get_settings") as mock_settings:
        mock_settings.return_value.s3_bucket_name = "test-bucket"
        mock_settings.return_value.s3_endpoint_url = None
        mock_settings.return_value.s3_region_name = "us-east-1"
        mock_settings.return_value.s3_access_key_id = "key"
        mock_settings.return_value.s3_secret_access_key = "secret"
        mock_settings.return_value.s3_public_cdn_url = ""
        mock_settings.return_value.s3_presigned_expiry_seconds = 3600

        storage = S3Storage(client=mock_boto_client)

        # Test delete
        await storage.delete("audio/test.mp3")
        mock_boto_client.delete_object.assert_called_once_with(Bucket="test-bucket", Key="audio/test.mp3")

        # Test get_presigned_upload_url
        res = await storage.get_presigned_upload_url("samples/my_voice.wav", content_type="audio/wav")
        assert res["upload_url"] == "https://r2.example.com/upload-signed-url"
        assert res["key"] == "samples/my_voice.wav"
        assert res["bucket"] == "test-bucket"


def test_storage_factory_and_retention(tmp_path):
    # Factory tests
    s3_storage = get_storage("s3")
    assert isinstance(s3_storage, S3Storage)

    r2_storage = get_storage("r2")
    assert isinstance(r2_storage, S3Storage)

    # Retention test
    test_storage_dir = tmp_path / "audio"
    test_storage_dir.mkdir(parents=True)
    old_file = test_storage_dir / "old_audio.mp3"
    old_file.write_bytes(b"old")

    with patch("app.services.storage_service.get_settings") as mock_settings:
        mock_settings.return_value.storage_path = str(test_storage_dir)
        mock_settings.return_value.storage_backend = "local"

        service = StorageService()
        # With days=0, old_file should be deleted
        cleaned = service.cleanup_old_local_files(days=-1)
        assert cleaned >= 1
