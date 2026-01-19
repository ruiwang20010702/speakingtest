"""
Tests for OSS Client
Covers: upload_audio, get_signed_url, delete_audio
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

from src.adapters.gateways.oss_client import OSSClient, UploadResult, upload_test_audio


class TestUploadResult:
    """Tests for UploadResult dataclass."""

    def test_create_success_result(self):
        """Test creating a success result."""
        result = UploadResult(
            success=True,
            url="https://bucket.oss.com/audio/test.mp3",
            key="audio/2025/01/19/123_part1_abc.mp3"
        )
        assert result.success is True
        assert result.url is not None
        assert result.error is None

    def test_create_error_result(self):
        """Test creating an error result."""
        result = UploadResult(
            success=False,
            error="Upload failed"
        )
        assert result.success is False
        assert result.url is None
        assert result.error == "Upload failed"


class TestOSSClientGenerateKey:
    """Tests for OSSClient._generate_key method."""

    @pytest.mark.asyncio
    async def test_generate_key_format(self):
        """Test key generation format."""
        with patch("src.adapters.gateways.oss_client.oss2"):
            client = OSSClient()
            key = client._generate_key(123, "part1", "mp3")

            assert key.startswith("audio/")
            assert "123" in key
            assert "part1" in key
            assert key.endswith(".mp3")

    @pytest.mark.asyncio
    async def test_generate_key_different_extensions(self):
        """Test key generation with different extensions."""
        with patch("src.adapters.gateways.oss_client.oss2"):
            client = OSSClient()

            key_mp3 = client._generate_key(1, "part1", "mp3")
            key_wav = client._generate_key(1, "part1", "wav")

            assert key_mp3.endswith(".mp3")
            assert key_wav.endswith(".wav")


class TestOSSClientUpload:
    """Tests for OSSClient.upload_audio method."""

    @pytest.mark.asyncio
    async def test_upload_audio_success(self):
        """Test successful audio upload."""
        with patch("src.adapters.gateways.oss_client.oss2") as mock_oss2:
            # Mock the bucket
            mock_bucket = MagicMock()
            mock_result = MagicMock()
            mock_result.status = 200
            mock_bucket.put_object.return_value = mock_result

            client = OSSClient()
            client.bucket = mock_bucket

            result = await client.upload_audio(
                audio_data=b"fake audio data",
                test_id=123,
                part="part1"
            )

            assert result.success is True
            assert result.url is not None
            assert "123" in result.key

    @pytest.mark.asyncio
    async def test_upload_audio_failure(self):
        """Test failed audio upload."""
        with patch("src.adapters.gateways.oss_client.oss2") as mock_oss2:
            mock_bucket = MagicMock()
            mock_result = MagicMock()
            mock_result.status = 500
            mock_bucket.put_object.return_value = mock_result

            client = OSSClient()
            client.bucket = mock_bucket

            result = await client.upload_audio(
                audio_data=b"fake audio data",
                test_id=123,
                part="part1"
            )

            assert result.success is False
            assert "500" in result.error

    @pytest.mark.asyncio
    async def test_upload_audio_exception(self):
        """Test upload with exception."""
        with patch("src.adapters.gateways.oss_client.oss2") as mock_oss2:
            # Define a real exception class for OssError to avoid TypeError
            class MockOssError(Exception):
                pass
            mock_oss2.exceptions.OssError = MockOssError

            mock_bucket = MagicMock()
            mock_bucket.put_object.side_effect = Exception("Connection error")

            client = OSSClient()
            client.bucket = mock_bucket

            result = await client.upload_audio(
                audio_data=b"fake audio data",
                test_id=123,
                part="part1"
            )

            assert result.success is False
            assert "Connection error" in result.error


class TestOSSClientSignedUrl:
    """Tests for OSSClient.get_signed_url method."""

    def test_get_signed_url(self):
        """Test signed URL generation."""
        with patch("src.adapters.gateways.oss_client.oss2"):
            mock_bucket = MagicMock()
            mock_bucket.sign_url.return_value = "https://signed-url.example.com"

            client = OSSClient()
            client.bucket = mock_bucket

            url = client.get_signed_url("audio/test.mp3")

            assert url == "https://signed-url.example.com"
            mock_bucket.sign_url.assert_called_once_with("GET", "audio/test.mp3", 3600)


class TestOSSClientDelete:
    """Tests for OSSClient.delete_audio method."""

    def test_delete_audio_success(self):
        """Test successful audio deletion."""
        with patch("src.adapters.gateways.oss_client.oss2"):
            mock_bucket = MagicMock()

            client = OSSClient()
            client.bucket = mock_bucket

            result = client.delete_audio("audio/test.mp3")

            assert result is True
            mock_bucket.delete_object.assert_called_once_with("audio/test.mp3")

    def test_delete_audio_failure(self):
        """Test failed audio deletion."""
        with patch("src.adapters.gateways.oss_client.oss2"):
            mock_bucket = MagicMock()
            mock_bucket.delete_object.side_effect = Exception("Delete failed")

            client = OSSClient()
            client.bucket = mock_bucket

            result = client.delete_audio("audio/test.mp3")

            assert result is False
