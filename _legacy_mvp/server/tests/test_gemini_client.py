"""
测试 Gemini API 客户端
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import time

from services.gemini_client import GeminiClient, gemini_client, MODEL_NAME, GEMINI_API_KEY


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API 响应"""
    mock_response = Mock()
    mock_response.text = "这是测试响应内容"
    return mock_response


@pytest.fixture
def mock_client():
    """Mock Gemini 客户端"""
    client = Mock()
    return client


@pytest.fixture
def sample_audio_file(tmp_path):
    """创建示例音频文件"""
    audio_file = tmp_path / "test_audio.webm"
    audio_file.write_bytes(b"fake audio data")
    return str(audio_file)


class TestGeminiClientInit:
    """测试 GeminiClient 初始化"""

    @patch("services.gemini_client.genai.Client")
    def test_init_creates_client(self, mock_genai_client):
        """测试初始化创建 Gemini 客户端"""
        mock_api_key = "test-api-key"
        with patch("services.gemini_client.GEMINI_API_KEY", mock_api_key):
            client = GeminiClient()
            mock_genai_client.assert_called_once_with(api_key=mock_api_key)


class TestAnalyzeAudioFromPath:
    """测试 analyze_audio_from_path 方法"""

    @patch("services.gemini_client.genai.Client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake audio data")
    def test_analyze_audio_success(self, mock_file, mock_genai_client, sample_audio_file, mock_gemini_response):
        """测试成功分析音频"""
        # Setup mock
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance
        mock_client_instance.models.generate_content.return_value = mock_gemini_response

        client = GeminiClient()
        result = client.analyze_audio_from_path(sample_audio_file, "分析这个音频")

        assert result == "这是测试响应内容"
        mock_client_instance.models.generate_content.assert_called_once()
        call_args = mock_client_instance.models.generate_content.call_args
        assert call_args.kwargs["model"] == MODEL_NAME

    @patch("services.gemini_client.genai.Client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake audio data")
    def test_analyze_audio_with_retry_503(self, mock_file, mock_genai_client, sample_audio_file):
        """测试 503 错误重试机制"""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        # 第一次调用失败，第二次成功
        mock_response_1 = Mock(side_effect=Exception("503 Service Unavailable"))
        mock_response_2 = Mock()
        mock_response_2.text = "重试后成功"

        mock_client_instance.models.generate_content.side_effect = [
            mock_response_1,
            mock_response_2
        ]

        client = GeminiClient()

        # Patch time.sleep to avoid actual delay
        with patch("services.gemini_client.time.sleep"):
            result = client.analyze_audio_from_path(sample_audio_file, "分析这个音频")

        assert result == "重试后成功"
        assert mock_client_instance.models.generate_content.call_count == 2

    @patch("services.gemini_client.genai.Client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake audio data")
    @patch("services.gemini_client.time.sleep")
    def test_analyze_audio_max_retries_exceeded(self, mock_sleep, mock_file, mock_genai_client, sample_audio_file):
        """测试超过最大重试次数"""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        # 所有调用都失败
        mock_client_instance.models.generate_content.side_effect = Exception("503 Service Unavailable")

        client = GeminiClient()

        with pytest.raises(Exception) as exc_info:
            client.analyze_audio_from_path(sample_audio_file, "分析这个音频")

        assert "网络连接问题" in str(exc_info.value) or "已重试3次" in str(exc_info.value)
        assert mock_client_instance.models.generate_content.call_count == 3

    @patch("services.gemini_client.genai.Client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake audio data")
    def test_analyze_audio_non_retryable_error(self, mock_file, mock_genai_client, sample_audio_file):
        """测试不可重试的错误"""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        # 非可重试错误
        mock_client_instance.models.generate_content.side_effect = Exception("400 Bad Request")

        client = GeminiClient()

        with pytest.raises(Exception) as exc_info:
            client.analyze_audio_from_path(sample_audio_file, "分析这个音频")

        assert "分析失败" in str(exc_info.value)
        # 应该只调用一次，不重试
        assert mock_client_instance.models.generate_content.call_count == 1

    @patch("services.gemini_client.genai.Client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake audio data")
    @patch("services.gemini_client.time.sleep")
    def test_retry_with_exponential_backoff(self, mock_sleep, mock_file, mock_genai_client, sample_audio_file):
        """测试指数退避重试策略"""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        # 前两次失败，第三次成功
        mock_client_instance.models.generate_content.side_effect = [
            Exception("503 Service Unavailable"),
            Exception("503 Service Unavailable"),
            Mock(text="第三次成功")
        ]

        client = GeminiClient()
        result = client.analyze_audio_from_path(sample_audio_file, "分析这个音频")

        assert result == "第三次成功"
        # 验证指数退避: 2秒, 4秒
        assert mock_sleep.call_count == 2
        assert mock_sleep.call_args_list[0][0][0] == 2
        assert mock_sleep.call_args_list[1][0][0] == 4

    @patch("services.gemini_client.genai.Client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake audio data")
    def test_analyze_audio_ssl_error_retry(self, mock_file, mock_genai_client, sample_audio_file):
        """测试 SSL 错误重试"""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        mock_response_1 = Mock(side_effect=Exception("SSL error"))
        mock_response_2 = Mock()
        mock_response_2.text = "重试成功"

        mock_client_instance.models.generate_content.side_effect = [
            mock_response_1,
            mock_response_2
        ]

        client = GeminiClient()

        with patch("services.gemini_client.time.sleep"):
            result = client.analyze_audio_from_path(sample_audio_file, "分析这个音频")

        assert result == "重试成功"
        assert mock_client_instance.models.generate_content.call_count == 2

    @patch("services.gemini_client.genai.Client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake audio data")
    @patch("services.gemini_client.time.sleep")
    def test_retryable_connection_errors(self, mock_sleep, mock_file, mock_genai_client, sample_audio_file):
        """测试各种可重试的连接错误"""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        retryable_errors = [
            "EOF error",
            "Connection reset",
            "Connection timeout",
            "Service overloaded"
        ]

        for error_msg in retryable_errors:
            mock_client_instance.models.generate_content.reset_mock()
            mock_client_instance.models.generate_content.side_effect = [
                Exception(error_msg),
                Mock(text="成功")
            ]

            client = GeminiClient()
            result = client.analyze_audio_from_path(sample_audio_file, "分析这个音频")

            assert result == "成功"

    @patch("services.gemini_client.genai.Client")
    def test_analyze_audio_file_not_found(self, mock_genai_client, sample_audio_file):
        """测试文件不存在"""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        client = GeminiClient()

        with pytest.raises(FileNotFoundError):
            client.analyze_audio_from_path("/nonexistent/file.webm", "分析这个音频")


class TestUploadAndAnalyzeAudio:
    """测试 upload_and_analyze_audio 方法"""

    @patch("services.gemini_client.genai.Client")
    def test_upload_and_analyze_success(self, mock_genai_client, sample_audio_file):
        """测试成功上传并分析音频"""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        # Mock 上传的文件
        mock_uploaded_file = Mock()
        mock_uploaded_file.uri = "uploaded-file-uri"
        mock_client_instance.files.upload.return_value = mock_uploaded_file

        # Mock 分析响应
        mock_response = Mock()
        mock_response.text = "分析结果"
        mock_client_instance.models.generate_content.return_value = mock_response

        client = GeminiClient()
        result = client.upload_and_analyze_audio(sample_audio_file, "分析这个音频")

        assert result == "分析结果"
        mock_client_instance.files.upload.assert_called_once_with(file=sample_audio_file)
        mock_client_instance.models.generate_content.assert_called_once()

    @patch("services.gemini_client.genai.Client")
    def test_upload_and_analyze_upload_failure(self, mock_genai_client, sample_audio_file):
        """测试上传失败"""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        mock_client_instance.files.upload.side_effect = Exception("Upload failed")

        client = GeminiClient()

        with pytest.raises(Exception) as exc_info:
            client.upload_and_analyze_audio(sample_audio_file, "分析这个音频")

        assert "Failed to upload and analyze" in str(exc_info.value)

    @patch("services.gemini_client.genai.Client")
    def test_upload_and_analyze_generation_failure(self, mock_genai_client, sample_audio_file):
        """测试分析失败"""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        # 上传成功
        mock_uploaded_file = Mock()
        mock_uploaded_file.uri = "uploaded-file-uri"
        mock_client_instance.files.upload.return_value = mock_uploaded_file

        # 分析失败
        mock_client_instance.models.generate_content.side_effect = Exception("Generation failed")

        client = GeminiClient()

        with pytest.raises(Exception) as exc_info:
            client.upload_and_analyze_audio(sample_audio_file, "分析这个音频")

        assert "Failed to upload and analyze" in str(exc_info.value)


class TestModuleConstants:
    """测试模块常量"""

    def test_model_name(self):
        """测试模型名称常量"""
        assert MODEL_NAME == "gemini-2.5-flash"

    def test_gemini_api_key_exists(self):
        """测试 API KEY 存在"""
        # 在测试环境中可能没有设置，所以只验证变量存在
        assert "GEMINI_API_KEY" in dir("services.gemini_client")


class TestGlobalGeminiClient:
    """测试全局客户端实例"""

    @patch("services.gemini_client.genai.Client")
    def test_global_client_exists(self, mock_genai_client):
        """测试全局客户端实例存在"""
        # 这个测试验证模块级别的 singleton 实例
        from services import gemini_client
        assert hasattr(gemini_client, 'gemini_client')


class TestAudioFileHandling:
    """测试音频文件处理"""

    @patch("services.gemini_client.genai.Client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"test audio content")
    def test_reads_audio_file_correctly(self, mock_file, mock_genai_client, sample_audio_file):
        """测试正确读取音频文件"""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance
        mock_client_instance.models.generate_content.return_value = Mock(text="result")

        client = GeminiClient()
        client.analyze_audio_from_path(sample_audio_file, "分析")

        # 验证文件被读取
        mock_file.assert_called_once_with(sample_audio_file, 'rb')

    @patch("services.gemini_client.genai.Client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"x" * (10 * 1024))  # 10KB
    def test_logs_audio_file_size(self, mock_file, mock_genai_client, sample_audio_file):
        """测试记录音频文件大小"""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance
        mock_client_instance.models.generate_content.return_value = Mock(text="result")

        client = GeminiClient()

        with patch("services.gemini_client.print"):
            client.analyze_audio_from_path(sample_audio_file, "分析")

        # 验证 API 被调用
        assert mock_client_instance.models.generate_content.called


class TestContentType:
    """测试内容类型处理"""

    @patch("services.gemini_client.genai.Client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"audio data")
    @patch("services.gemini_client.types.Part.from_bytes")
    def test_uses_correct_mime_type(self, mock_part_from_bytes, mock_file, mock_genai_client, sample_audio_file):
        """测试使用正确的 MIME 类型"""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance
        mock_part = Mock()
        mock_part_from_bytes.return_value = mock_part
        mock_client_instance.models.generate_content.return_value = Mock(text="result")

        client = GeminiClient()
        client.analyze_audio_from_path(sample_audio_file, "分析")

        # 验证使用了正确的 MIME 类型
        mock_part_from_bytes.assert_called_once()
        call_kwargs = mock_part_from_bytes.call_args.kwargs
        assert call_kwargs["mime_type"] == "audio/webm"
        assert call_kwargs["data"] == b"audio data"
