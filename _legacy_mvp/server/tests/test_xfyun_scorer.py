"""
测试讯飞语音评分服务
"""
import pytest
from unittest.mock import Mock, patch
from typing import Dict, List

from services.xfyun_scorer import (
    evaluate_words_with_xfyun,
    evaluate_sentence_with_xfyun,
    evaluate_part2_all_with_xfyun,
    _get_dp_message_text,
    _generate_part1_feedback,
    _generate_part2_feedback,
    _generate_part2_overall_feedback,
    is_xfyun_configured
)


@pytest.fixture
def mock_audio_path(tmp_path):
    """模拟音频文件路径"""
    audio_file = tmp_path / "test_audio.wav"
    audio_file.write_bytes(b"fake audio")
    return str(audio_file)


@pytest.fixture
def mock_xfyun_result_success():
    """Mock 成功的讯飞评测结果"""
    return {
        "status": "success",
        "data": {
            "total_score": 85.0,
            "accuracy_score": 88.0,
            "fluency_score": 83.0,
            "integrity_score": 86.0,
            "details": [
                {"content": "hello", "total_score": 90.0, "dp_message": "0"},
                {"content": "world", "total_score": 85.0, "dp_message": "0"},
                {"content": "test", "total_score": 80.0, "dp_message": "0"}
            ]
        }
    }


class TestEvaluateWordsWithXfyun:
    """测试 evaluate_words_with_xfyun 函数"""

    @patch("services.xfyun_scorer.get_xfyun_client")
    def test_evaluate_words_success(self, mock_get_client, mock_audio_path, mock_xfyun_result_success):
        """测试成功评估单词"""
        mock_client = Mock()
        mock_client.evaluate_audio.return_value = mock_xfyun_result_success
        mock_get_client.return_value = mock_client

        words = ["hello", "world", "test"]
        result = evaluate_words_with_xfyun(mock_audio_path, words)

        assert result["score"] == 3  # 所有单词正确
        assert result["total"] == 3
        assert len(result["correct_words"]) == 3
        assert len(result["incorrect_words"]) == 0
        assert "feedback" in result

    @patch("services.xfyun_scorer.get_xfyun_client")
    def test_evaluate_words_partial_correct(self, mock_get_client, mock_audio_path):
        """测试部分单词正确"""
        mock_result = {
            "status": "success",
            "data": {
                "accuracy_score": 70.0,
                "fluency_score": 65.0,
                "details": [
                    {"content": "hello", "total_score": 90.0, "dp_message": "0"},
                    {"content": "world", "total_score": 40.0, "dp_message": "16"},  # 漏读
                    {"content": "test", "total_score": 85.0, "dp_message": "0"}
                ]
            }
        }

        mock_client = Mock()
        mock_client.evaluate_audio.return_value = mock_result
        mock_get_client.return_value = mock_client

        words = ["hello", "world", "test"]
        result = evaluate_words_with_xfyun(mock_audio_path, words)

        assert result["score"] == 2  # 2个正确
        assert len(result["correct_words"]) == 2
        assert len(result["incorrect_words"]) == 1
        assert result["incorrect_words"][0] == "world"

    @patch("services.xfyun_scorer.get_xfyun_client")
    def test_evaluate_words_client_none(self, mock_get_client, mock_audio_path):
        """测试客户端未配置"""
        mock_get_client.return_value = None

        result = evaluate_words_with_xfyun(mock_audio_path, ["hello", "world"])

        assert result["score"] == 0
        assert "error" in result
        assert "未配置" in result["error"]

    @patch("services.xfyun_scorer.get_xfyun_client")
    def test_evaluate_words_api_error(self, mock_get_client, mock_audio_path):
        """测试 API 错误"""
        mock_client = Mock()
        mock_client.evaluate_audio.return_value = {
            "status": "error",
            "error": "Connection failed"
        }
        mock_get_client.return_value = mock_client

        result = evaluate_words_with_xfyun(mock_audio_path, ["hello"])

        assert result["score"] == 0
        assert "error" in result

    @patch("services.xfyun_scorer.get_xfyun_client")
    def test_evaluate_words_exception(self, mock_get_client, mock_audio_path):
        """测试异常处理"""
        mock_client = Mock()
        mock_client.evaluate_audio.side_effect = Exception("Unexpected error")
        mock_get_client.return_value = mock_client

        result = evaluate_words_with_xfyun(mock_audio_path, ["hello"])

        assert result["score"] == 0
        assert "error" in result

    @patch("services.xfyun_scorer.get_xfyun_client")
    def test_evaluate_words_low_score(self, mock_get_client, mock_audio_path):
        """测试低分单词（低于60分视为错误）"""
        mock_result = {
            "status": "success",
            "data": {
                "accuracy_score": 50.0,
                "fluency_score": 45.0,
                "details": [
                    {"content": "hello", "total_score": 90.0, "dp_message": "0"},
                    {"content": "world", "total_score": 50.0, "dp_message": "0"},  # 低于60分
                    {"content": "test", "total_score": 30.0, "dp_message": "0"}
                ]
            }
        }

        mock_client = Mock()
        mock_client.evaluate_audio.return_value = mock_result
        mock_get_client.return_value = mock_client

        words = ["hello", "world", "test"]
        result = evaluate_words_with_xfyun(mock_audio_path, words)

        assert result["score"] == 1  # 只有1个正确


class TestEvaluateSentenceWithXfyun:
    """测试 evaluate_sentence_with_xfyun 函数"""

    @patch("services.xfyun_scorer.get_xfyun_client")
    def test_evaluate_sentence_success(self, mock_get_client, mock_audio_path):
        """测试成功评估句子"""
        mock_result = {
            "status": "success",
            "data": {
                "total_score": 85.0,
                "accuracy_score": 88.0,
                "fluency_score": 83.0,
                "details": []
            }
        }

        mock_client = Mock()
        mock_client.evaluate_audio.return_value = mock_result
        mock_get_client.return_value = mock_client

        result = evaluate_sentence_with_xfyun(mock_audio_path, "What's your name?", 0)

        assert "scores" in result
        assert result["scores"]["pronunciation"] > 0
        assert result["scores"]["fluency"] > 0
        assert "raw_scores" in result

    @patch("services.xfyun_scorer.get_xfyun_client")
    def test_evaluate_sentence_score_conversion(self, mock_get_client, mock_audio_path):
        """测试分数转换（0-100 转 0-2）"""
        mock_result = {
            "status": "success",
            "data": {
                "total_score": 50.0,
                "accuracy_score": 50.0,
                "fluency_score": 50.0,
                "details": []
            }
        }

        mock_client = Mock()
        mock_client.evaluate_audio.return_value = mock_result
        mock_get_client.return_value = mock_client

        result = evaluate_sentence_with_xfyun(mock_audio_path, "Test question")

        # 50/100 * 2 = 1.0
        assert result["scores"]["pronunciation"] == 1.0
        assert result["scores"]["fluency"] == 1.0

    @patch("services.xfyun_scorer.get_xfyun_client")
    def test_evaluate_sentence_client_none(self, mock_get_client, mock_audio_path):
        """测试客户端未配置"""
        mock_get_client.return_value = None

        result = evaluate_sentence_with_xfyun(mock_audio_path, "Test question")

        assert result["scores"]["pronunciation"] == 0
        assert result["scores"]["fluency"] == 0
        assert "error" in result

    @patch("services.xfyun_scorer.get_xfyun_client")
    def test_evaluate_sentence_with_index(self, mock_get_client, mock_audio_path):
        """测试带问题索引的评估"""
        mock_result = {
            "status": "success",
            "data": {
                "total_score": 75.0,
                "accuracy_score": 75.0,
                "fluency_score": 75.0,
                "details": []
            }
        }

        mock_client = Mock()
        mock_client.evaluate_audio.return_value = mock_result
        mock_get_client.return_value = mock_client

        result = evaluate_sentence_with_xfyun(mock_audio_path, "Question 5", 4)

        assert "feedback" in result


class TestEvaluatePart2AllWithXfyun:
    """测试 evaluate_part2_all_with_xfyun 函数"""

    @patch("services.xfyun_scorer.get_xfyun_client")
    def test_evaluate_part2_all_success(self, mock_get_client, mock_audio_path):
        """测试成功评估整个 Part 2"""
        mock_result = {
            "status": "success",
            "data": {
                "total_score": 80.0,
                "accuracy_score": 82.0,
                "fluency_score": 78.0,
                "details": []
            }
        }

        mock_client = Mock()
        mock_client.evaluate_audio.return_value = mock_result
        mock_get_client.return_value = mock_client

        questions = [f"Question {i}" for i in range(1, 13)]
        result = evaluate_part2_all_with_xfyun(mock_audio_path, questions)

        assert len(result["question_scores"]) == 12
        assert result["total_score"] > 0
        assert "summary" in result

    @patch("services.xfyun_scorer.get_xfyun_client")
    def test_evaluate_part2_all_score_distribution(self, mock_get_client, mock_audio_path):
        """测试分数分配给每个问题"""
        mock_result = {
            "status": "success",
            "data": {
                "total_score": 75.0,
                "accuracy_score": 75.0,
                "fluency_score": 75.0,
                "details": []
            }
        }

        mock_client = Mock()
        mock_client.evaluate_audio.return_value = mock_result
        mock_get_client.return_value = mock_client

        questions = [f"Q{i}" for i in range(12)]
        result = evaluate_part2_all_with_xfyun(mock_audio_path, questions)

        # 每个问题应该得到相同的分数
        first_score = result["question_scores"][0]["score"]
        for qs in result["question_scores"]:
            assert qs["score"] == first_score

    @patch("services.xfyun_scorer.get_xfyun_client")
    def test_evaluate_part2_all_client_none(self, mock_get_client, mock_audio_path):
        """测试客户端未配置"""
        mock_get_client.return_value = None

        result = evaluate_part2_all_with_xfyun(mock_audio_path, ["Q1", "Q2"])

        assert result["total_score"] == 0
        assert "error" in result

    @patch("services.xfyun_scorer.get_xfyun_client")
    def test_evaluate_part2_all_uses_chapter_mode(self, mock_get_client, mock_audio_path):
        """测试使用篇章模式"""
        mock_result = {
            "status": "success",
            "data": {
                "total_score": 80.0,
                "accuracy_score": 80.0,
                "fluency_score": 80.0,
                "details": []
            }
        }

        mock_client = Mock()
        mock_client.evaluate_audio.return_value = mock_result
        mock_get_client.return_value = mock_client

        questions = [f"Question {i}" for i in range(1, 13)]
        evaluate_part2_all_with_xfyun(mock_audio_path, questions)

        # 验证使用了 read_chapter 类别
        mock_client.evaluate_audio.assert_called_once()
        call_kwargs = mock_client.evaluate_audio.call_args.kwargs
        assert call_kwargs["category"] == "read_chapter"


class TestGetDpMessageText:
    """测试 _get_dp_message_text 函数"""

    def test_dp_message_correct(self):
        """测试正确标记"""
        assert _get_dp_message_text("0") == "正确"

    def test_dp_message_missed(self):
        """测试漏读标记"""
        assert _get_dp_message_text("16") == "漏读"

    def test_dp_message_added(self):
        """测试增读标记"""
        assert _get_dp_message_text("32") == "增读"

    def test_dp_message_repeated(self):
        """测试回读标记"""
        assert _get_dp_message_text("64") == "回读"

    def test_dp_message_replaced(self):
        """测试替换标记"""
        assert _get_dp_message_text("128") == "替换"

    def test_dp_message_unknown(self):
        """测试未知标记"""
        assert _get_dp_message_text("255") == "未知"


class TestGeneratePart1Feedback:
    """测试 _generate_part1_feedback 函数"""

    def test_feedback_all_correct(self):
        """测试全部正确"""
        word_results = [
            {"word": "hello", "correct": True, "score": 90},
            {"word": "world", "correct": True, "score": 85},
            {"word": "test", "correct": True, "score": 88}
        ]
        data = {"accuracy_score": 88.0}

        feedback = _generate_part1_feedback(word_results, data)

        assert "优秀" in feedback
        assert "3 个单词都发音正确" in feedback

    def test_feedback_mostly_correct(self):
        """测试大部分正确（80%以上）"""
        word_results = [
            {"word": "hello", "correct": True, "score": 90},
            {"word": "world", "correct": True, "score": 85},
            {"word": "test", "correct": False, "score": 40},
            {"word": "good", "correct": True, "score": 88},
            {"word": "bad", "correct": True, "score": 82}
        ]
        data = {"accuracy_score": 75.0}

        feedback = _generate_part1_feedback(word_results, data)

        assert "良好" in feedback
        assert "4/5" in feedback
        assert "test" in feedback  # 包含错误的单词

    def test_feedback_half_correct(self):
        """测试一半正确（50%-80%）"""
        word_results = [
            {"word": "hello", "correct": True, "score": 70},
            {"word": "world", "correct": False, "score": 40},
            {"word": "test", "correct": True, "score": 65},
            {"word": "good", "correct": False, "score": 35}
        ]
        data = {"accuracy_score": 55.0}

        feedback = _generate_part1_feedback(word_results, data)

        assert "有待提高" in feedback
        assert "2/4" in feedback

    def test_feedback_poor(self):
        """测试表现差（50%以下）"""
        word_results = [
            {"word": "hello", "correct": False, "score": 40},
            {"word": "world", "correct": False, "score": 30},
            {"word": "test", "correct": True, "score": 55}
        ]
        data = {"accuracy_score": 40.0}

        feedback = _generate_part1_feedback(word_results, data)

        assert "需要加强练习" in feedback
        assert "1/3" in feedback


class TestGeneratePart2Feedback:
    """测试 _generate_part2_feedback 函数"""

    def test_feedback_excellent(self):
        """测试优秀反馈"""
        feedback = _generate_part2_feedback(85.0, 88.0)
        assert "优秀" in feedback

    def test_feedback_good(self):
        """测试良好反馈"""
        feedback = _generate_part2_feedback(70.0, 65.0)
        assert "良好" in feedback

    def test_feedback_average(self):
        """测试一般反馈"""
        feedback = _generate_part2_feedback(50.0, 45.0)
        assert "有待提高" in feedback

    def test_feedback_poor(self):
        """测试差评反馈"""
        feedback = _generate_part2_feedback(30.0, 35.0)
        assert "需要加强练习" in feedback or "基础句型" in feedback


class TestGeneratePart2OverallFeedback:
    """测试 _generate_part2_overall_feedback 函数"""

    def test_overall_feedback_excellent(self):
        """测试优秀整体反馈"""
        feedback = _generate_part2_overall_feedback(85.0, 88.0, 12)
        assert "表现优秀" in feedback
        assert "发音准确度较高" in feedback
        assert "表达流利自然" in feedback

    def test_overall_feedback_good(self):
        """测试良好整体反馈"""
        feedback = _generate_part2_overall_feedback(70.0, 65.0, 12)
        assert "表现良好" in feedback

    def test_overall_feedback_average(self):
        """测试一般整体反馈"""
        feedback = _generate_part2_overall_feedback(50.0, 45.0, 12)
        assert "进步空间" in feedback or "继续加强练习" in feedback

    def test_overall_feedback_low_accuracy(self):
        """测试低准确度反馈"""
        feedback = _generate_part2_overall_feedback(60.0, 75.0, 12)
        assert "提高发音准确度" in feedback

    def test_overall_feedback_low_fluency(self):
        """测试低流利度反馈"""
        feedback = _generate_part2_overall_feedback(75.0, 60.0, 12)
        assert "提高表达的流利度" in feedback

    def test_overall_feedback_combined(self):
        """测试组合反馈"""
        feedback = _generate_part2_overall_feedback(50.0, 55.0, 12)
        # 应该包含多个反馈部分
        assert "12" in feedback  # 问题数量


class TestIsXfyunConfigured:
    """测试 is_xfyun_configured 函数"""

    @patch("services.xfyun_scorer.get_xfyun_client")
    def test_configured(self, mock_get_client):
        """测试已配置"""
        mock_get_client.return_value = Mock()
        assert is_xfyun_configured() is True

    @patch("services.xfyun_scorer.get_xfyun_client")
    def test_not_configured(self, mock_get_client):
        """测试未配置"""
        mock_get_client.return_value = None
        assert is_xfyun_configured() is False


class TestScoreCalculations:
    """测试分数计算"""

    @patch("services.xfyun_scorer.get_xfyun_client")
    def test_part2_score_calculation(self, mock_get_client, mock_audio_path):
        """测试 Part 2 分数计算"""
        mock_result = {
            "status": "success",
            "data": {
                "total_score": 100.0,
                "accuracy_score": 100.0,
                "fluency_score": 100.0,
                "details": []
            }
        }

        mock_client = Mock()
        mock_client.evaluate_audio.return_value = mock_result
        mock_get_client.return_value = mock_client

        questions = [f"Q{i}" for i in range(12)]
        result = evaluate_part2_all_with_xfyun(mock_audio_path, questions)

        # 满分应该是 24 (12个问题，每个2分)
        assert result["total_score"] == 24.0
        # 每个问题应该是2分
        assert result["question_scores"][0]["score"] == 2.0

    @patch("services.xfyun_scorer.get_xfyun_client")
    def test_part2_half_score(self, mock_get_client, mock_audio_path):
        """测试 Part 2 一半分数"""
        mock_result = {
            "status": "success",
            "data": {
                "total_score": 50.0,
                "accuracy_score": 50.0,
                "fluency_score": 50.0,
                "details": []
            }
        }

        mock_client = Mock()
        mock_client.evaluate_audio.return_value = mock_result
        mock_get_client.return_value = mock_client

        questions = [f"Q{i}" for i in range(12)]
        result = evaluate_part2_all_with_xfyun(mock_audio_path, questions)

        # 50% 分数应该是 12
        assert result["total_score"] == 12.0
