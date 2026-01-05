"""
测试讯飞语音评测客户端
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
import base64
import json
from xml.etree import ElementTree as ET

from services.xfyun_client import (
    XfyunIseClient,
    get_xfyun_client,
    ISE_URL,
    XFYUN_APP_ID,
    XFYUN_API_KEY,
    XFYUN_API_SECRET
)


@pytest.fixture
def mock_xfyun_config():
    """Mock 讯飞 API 配置"""
    return {
        "app_id": "test_app_id",
        "api_key": "test_api_key",
        "api_secret": "test_api_secret"
    }


@pytest.fixture
def sample_audio_file(tmp_path):
    """创建示例音频文件"""
    audio_file = tmp_path / "test_audio.wav"
    audio_file.write_bytes(b"fake wav data")
    return str(audio_file)


@pytest.fixture
def sample_xml_result():
    """示例 XML 评测结果"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rec_paper total_score="85.5" accuracy_score="88.0" fluency_score="83.0" integrity_score="86.0">
    <read_sentence>
        <sentence total_score="85.5">
            <word content="hello" total_score="90.0" dp_message="0">
                <syll content="hel" total_score="92.0"/>
                <syll content="lo" total_score="88.0"/>
            </word>
            <word content="world" total_score="81.0" dp_message="0">
                <syll content="wor" total_score="83.0"/>
                <syll content="ld" total_score="79.0"/>
            </word>
        </sentence>
    </read_sentence>
</rec_paper>"""


class TestXfyunIseClientInit:
    """测试 XfyunIseClient 初始化"""

    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    def test_init_success(self):
        """测试成功初始化"""
        client = XfyunIseClient()
        assert client.app_id == "test_app_id"
        assert client.api_key == "test_api_key"
        assert client.api_secret == "test_api_secret"

    @patch("services.xfyun_client.XFYUN_APP_ID", "")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    def test_init_missing_app_id(self):
        """测试缺少 APP_ID"""
        with pytest.raises(ValueError) as exc_info:
            XfyunIseClient()
        assert "配置不完整" in str(exc_info.value)

    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    def test_init_missing_api_key(self):
        """测试缺少 API_KEY"""
        with pytest.raises(ValueError) as exc_info:
            XfyunIseClient()
        assert "配置不完整" in str(exc_info.value)


class TestCreateUrl:
    """测试 _create_url 方法"""

    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    @patch("services.xfyun_client.datetime")
    def test_create_url_structure(self, mock_datetime):
        """测试生成 URL 结构"""
        mock_now = Mock()
        mock_now.strftime.return_value = "Mon, 01 Jan 2024 00:00:00 GMT"
        mock_datetime.datetime.now.return_value = mock_now

        client = XfyunIseClient()
        url = client._create_url()

        assert "wss://ise-api.xfyun.cn/v2/open-ise" in url
        assert "authorization=" in url
        assert "date=" in url
        assert "host=" in url


class TestBuildIseText:
    """测试 _build_ise_text 方法"""

    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    def test_build_word_text(self):
        """测试构建单词评测文本"""
        client = XfyunIseClient()
        result = client._build_ise_text("hello", "read_word")
        assert result == "[word]hello[/word]"

    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    def test_build_sentence_text(self):
        """测试构建句子评测文本"""
        client = XfyunIseClient()
        result = client._build_ise_text("Hello world", "read_sentence")
        assert result == "[sent]Hello world[/sent]"

    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    def test_build_chapter_text(self):
        """测试构建篇章评测文本"""
        client = XfyunIseClient()
        result = client._build_ise_text("Long text", "read_chapter")
        assert result == "[chapter]Long text[/chapter]"

    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    def test_build_unknown_category(self):
        """测试未知类别返回原文本"""
        client = XfyunIseClient()
        result = client._build_ise_text("test", "unknown")
        assert result == "test"


class TestParseResult:
    """测试 _parse_result 方法"""

    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    def test_parse_sentence_result(self, sample_xml_result):
        """测试解析句子评测结果"""
        client = XfyunIseClient()
        result = client._parse_result(sample_xml_result)

        assert result["total_score"] == 85.5
        assert result["accuracy_score"] == 88.0
        assert result["fluency_score"] == 83.0
        assert result["integrity_score"] == 86.0
        assert len(result["details"]) == 2
        assert result["details"][0]["content"] == "hello"
        assert result["details"][0]["total_score"] == 90.0
        assert result["details"][1]["content"] == "world"

    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    def test_parse_word_result(self):
        """测试解析单词评测结果"""
        xml = """<?xml version="1.0"?>
        <rec_paper total_score="90.0">
            <read_word>
                <word content="hello" total_score="90.0"/>
            </read_word>
        </rec_paper>"""

        client = XfyunIseClient()
        result = client._parse_result(xml)

        assert result["total_score"] == 90.0
        assert len(result["details"]) == 1
        assert result["details"][0]["content"] == "hello"

    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    def test_parse_invalid_xml(self):
        """测试解析无效 XML"""
        client = XfyunIseClient()
        result = client._parse_result("invalid xml")

        assert "error" in result
        assert "解析 XML 失败" in result["error"]

    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    def test_parse_syllable_details(self, sample_xml_result):
        """测试解析音素详情"""
        client = XfyunIseClient()
        result = client._parse_result(sample_xml_result)

        # 检查第一个单词的音素
        assert "syllables" in result["details"][0]
        assert len(result["details"][0]["syllables"]) == 2
        assert result["details"][0]["syllables"][0]["content"] == "hel"
        assert result["details"][0]["syllables"][0]["score"] == 92.0

    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    def test_parse_dp_message(self, sample_xml_result):
        """测试解析 dp_message (错误类型)"""
        client = XfyunIseClient()
        result = client._parse_result(sample_xml_result)

        # dp_message=0 表示正确
        assert result["details"][0]["dp_message"] == "0"


class TestPrepareAudio:
    """测试 _prepare_audio 方法"""

    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    def test_prepare_pcm_audio(self, sample_audio_file):
        """测试准备 PCM 音频"""
        # 将文件改为 .pcm 扩展名
        pcm_file = sample_audio_file.replace(".wav", ".pcm")
        import os
        os.rename(sample_audio_file, pcm_file)

        with open(pcm_file, "wb") as f:
            f.write(b"pcm data")

        client = XfyunIseClient()
        result = client._prepare_audio(pcm_file)

        assert result == b"pcm data"

    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    @patch("services.xfyun_client.AudioSegment")
    def test_prepare_wav_audio(self, mock_audio_segment, sample_audio_file):
        """测试准备 WAV 音频"""
        mock_audio = Mock()
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_sample_width.return_value = mock_audio
        mock_audio.raw_data = b"converted pcm data"
        mock_audio_segment.from_wav.return_value = mock_audio

        client = XfyunIseClient()
        result = client._prepare_audio(sample_audio_file)

        mock_audio_segment.from_wav.assert_called_once_with(sample_audio_file)
        mock_audio.set_frame_rate.assert_called_once_with(16000)
        mock_audio.set_channels.assert_called_once_with(1)
        assert result == b"converted pcm data"

    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    @patch("services.xfyun_client.AudioSegment")
    def test_prepare_webm_audio(self, mock_audio_segment, sample_audio_file):
        """测试准备 WebM 音频"""
        # 重命名为 .webm
        webm_file = sample_audio_file.replace(".wav", ".webm")
        import os
        os.rename(sample_audio_file, webm_file)

        mock_audio = Mock()
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_sample_width.return_value = mock_audio
        mock_audio.raw_data = b"webm pcm data"
        mock_audio_segment.from_file.return_value = mock_audio

        client = XfyunIseClient()
        result = client._prepare_audio(webm_file)

        mock_audio_segment.from_file.assert_called_once_with(webm_file, format='webm')
        assert result == b"webm pcm data"


class TestEvaluateAudio:
    """测试 evaluate_audio 方法"""

    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    @patch("services.xfyun_client.websocket.WebSocketApp")
    @patch("services.xfyun_client.AudioSegment")
    def test_evaluate_audio_success(self, mock_audio_segment, mock_websocket_app, sample_audio_file):
        """测试成功评测音频"""
        # Mock audio
        mock_audio = Mock()
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_sample_width.return_value = mock_audio
        mock_audio.raw_data = b"audio data"
        mock_audio_segment.from_wav.return_value = mock_audio

        # Mock WebSocket
        mock_ws = Mock()
        mock_websocket_app.return_value = mock_ws

        # Mock response callback
        def mock_run_forever(**kwargs):
            # 模拟服务器响应
            response = {
                "code": 0,
                "data": {
                    "status": 2,  # 评测结束
                    "data": base64.b64encode(
                        b'<?xml version="1.0"?><rec_paper total_score="85.5"/>'
                    ).decode('utf-8')
                }
            }
            # 调用 on_message
            mock_ws.on_message(mock_ws, json.dumps(response))

        mock_ws.run_forever = mock_run_forever

        client = XfyunIseClient()
        result = client.evaluate_audio(sample_audio_file, "hello world")

        assert result["status"] == "success"
        assert result["data"]["total_score"] == 85.5

    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    @patch("services.xfyun_client.websocket.WebSocketApp")
    @patch("services.xfyun_client.AudioSegment")
    def test_evaluate_audio_error_code(self, mock_audio_segment, mock_websocket_app, sample_audio_file):
        """测试评测返回错误码"""
        mock_audio = Mock()
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_sample_width.return_value = mock_audio
        mock_audio.raw_data = b"audio data"
        mock_audio_segment.from_wav.return_value = mock_audio

        mock_ws = Mock()
        mock_websocket_app.return_value = mock_ws

        def mock_run_forever(**kwargs):
            response = {
                "code": 101,
                "message": "Invalid parameter"
            }
            mock_ws.on_message(mock_ws, json.dumps(response))

        mock_ws.run_forever = mock_run_forever

        client = XfyunIseClient()
        result = client.evaluate_audio(sample_audio_file, "hello")

        assert result["status"] == "error"
        assert "101" in result["error"]

    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    @patch("services.xfyun_client.websocket.WebSocketApp")
    @patch("services.xfyun_client.AudioSegment")
    def test_evaluate_audio_websocket_error(self, mock_audio_segment, mock_websocket_app, sample_audio_file):
        """测试 WebSocket 错误"""
        mock_audio = Mock()
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_sample_width.return_value = mock_audio
        mock_audio.raw_data = b"audio data"
        mock_audio_segment.from_wav.return_value = mock_audio

        mock_ws = Mock()
        mock_websocket_app.return_value = mock_ws

        def mock_run_forever(**kwargs):
            mock_ws.on_error(mock_ws, "Connection failed")

        mock_ws.run_forever = mock_run_forever

        client = XfyunIseClient()
        result = client.evaluate_audio(sample_audio_file, "hello")

        assert result["status"] == "error"
        assert "WebSocket 错误" in result["error"]


class TestEvaluateAudioParameters:
    """测试评测参数"""

    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    @patch("services.xfyun_client.websocket.WebSocketApp")
    @patch("services.xfyun_client.AudioSegment")
    def test_evaluate_with_category_read_word(self, mock_audio_segment, mock_websocket_app, sample_audio_file):
        """测试单词评测"""
        mock_audio = Mock()
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_sample_width.return_value = mock_audio
        mock_audio.raw_data = b"audio data"
        mock_audio_segment.from_wav.return_value = mock_audio

        mock_ws = Mock()
        mock_websocket_app.return_value = mock_ws

        sent_frames = []

        def mock_send(data):
            sent_frames.append(json.loads(data))

        def mock_run_forever(**kwargs):
            mock_ws.send = mock_send
            response = {
                "code": 0,
                "data": {"status": 2, "data": base64.b64encode(b'<rec_paper total_score="90.0"/>').decode()}
            }
            mock_ws.on_message(mock_ws, json.dumps(response))

        mock_ws.run_forever = mock_run_forever

        client = XfyunIseClient()
        result = client.evaluate_audio(sample_audio_file, "hello", category="read_word")

        # 验证第一帧包含正确的 category
        first_frame = sent_frames[0]
        assert first_frame["business"]["category"] == "read_word"

    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    @patch("services.xfyun_client.websocket.WebSocketApp")
    @patch("services.xfyun_client.AudioSegment")
    def test_evaluate_with_language_chinese(self, mock_audio_segment, mock_websocket_app, sample_audio_file):
        """测试中文评测"""
        mock_audio = Mock()
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_sample_width.return_value = mock_audio
        mock_audio.raw_data = b"audio data"
        mock_audio_segment.from_wav.return_value = mock_audio

        mock_ws = Mock()
        mock_websocket_app.return_value = mock_ws

        sent_frames = []

        def mock_send(data):
            sent_frames.append(json.loads(data))

        def mock_run_forever(**kwargs):
            mock_ws.send = mock_send
            response = {
                "code": 0,
                "data": {"status": 2, "data": base64.b64encode(b'<rec_paper total_score="85.0"/>').decode()}
            }
            mock_ws.on_message(mock_ws, json.dumps(response))

        mock_ws.run_forever = mock_run_forever

        client = XfyunIseClient()
        result = client.evaluate_audio(sample_audio_file, "你好", category="read_sentence", language="zh_cn")

        # 验证使用中文引擎
        first_frame = sent_frames[0]
        assert first_frame["business"]["ent"] == "cn_vip"


class TestGetGlobalClient:
    """测试全局客户端实例"""

    @patch("services.xfyun_client.xfyun_client", None)
    @patch("services.xfyun_client.XFYUN_APP_ID", "test_app_id")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    def test_get_client_first_time(self):
        """测试首次获取客户端"""
        client = get_xfyun_client()
        assert client is not None
        assert isinstance(client, XfyunIseClient)

    @patch("services.xfyun_client.XFYUN_APP_ID", "")
    @patch("services.xfyun_client.XFYUN_API_KEY", "test_api_key")
    @patch("services.xfyun_client.XFYUN_API_SECRET", "test_api_secret")
    @patch("services.xfyun_client.print")
    def test_get_client_missing_config(self, mock_print):
        """测试配置缺失时返回 None"""
        result = get_xfyun_client()
        assert result is None
        # 验证打印了错误信息
        mock_print.assert_called()


class TestModuleConstants:
    """测试模块常量"""

    def test_ise_url(self):
        """测试 WebSocket URL"""
        assert ISE_URL == "wss://ise-api.xfyun.cn/v2/open-ise"
