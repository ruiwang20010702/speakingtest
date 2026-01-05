"""
测试 Part 3 评估函数
"""
import pytest
from unittest.mock import Mock, patch, call
from typing import Dict

from services.part3_evaluator import (
    evaluate_part3_single_question,
    evaluate_part3_group,
    evaluate_part2_all
)


@pytest.fixture
def sample_dialogue():
    """示例对话数据"""
    return {
        "teacher": "What's your favorite food?",
        "student_options": ["I like pizza", "I love sushi", "My favorite is pasta"]
    }


@pytest.fixture
def sample_dialogues_part3():
    """Part 3 对话数据（6个问题）"""
    return [
        {"teacher": f"Question {i}", "student_options": [f"Answer {i}A", f"Answer {i}B"]}
        for i in range(1, 7)
    ]


@pytest.fixture
def sample_dialogues_part2():
    """Part 2 对话数据（12个问题）"""
    return [
        {"teacher": f"Question {i}", "student_options": [f"Answer {i}A", f"Answer {i}B"]}
        for i in range(1, 13)
    ]


@pytest.fixture
def mock_audio_path(tmp_path):
    """模拟音频文件路径"""
    audio_file = tmp_path / "test_audio.m4a"
    audio_file.write_bytes(b"fake audio")
    return str(audio_file)


class TestEvaluatePart3SingleQuestion:
    """测试 evaluate_part3_single_question 函数"""

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    def test_evaluate_single_question_success(self, mock_parse, mock_client, sample_dialogue, mock_audio_path):
        """测试成功评估单个问题"""
        # Setup mocks
        mock_gemini_response = {"score": 2, "student_answer": "I like pizza", "feedback": "很好"}
        mock_parse.return_value = mock_gemini_response

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "mocked response"

        score, result = evaluate_part3_single_question(mock_audio_path, sample_dialogue, 1)

        assert score == 2
        assert result["student_answer"] == "I like pizza"
        assert result["feedback"] == "很好"
        mock_client_instance.analyze_audio_from_path.assert_called_once()

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    def test_evaluate_single_question_partial_score(self, mock_parse, mock_client, sample_dialogue, mock_audio_path):
        """测试部分正确得分"""
        mock_gemini_response = {"score": 1, "student_answer": "Pizza", "feedback": "不完整"}
        mock_parse.return_value = mock_gemini_response

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "response"

        score, result = evaluate_part3_single_question(mock_audio_path, sample_dialogue, 5)

        assert score == 1
        assert result["feedback"] == "不完整"

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    def test_evaluate_single_question_zero_score(self, mock_parse, mock_client, sample_dialogue, mock_audio_path):
        """测试零分"""
        mock_gemini_response = {"score": 0, "student_answer": "", "feedback": "无法回答"}
        mock_parse.return_value = mock_gemini_response

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "response"

        score, result = evaluate_part3_single_question(mock_audio_path, sample_dialogue, 3)

        assert score == 0
        assert result["feedback"] == "无法回答"

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    def test_evaluate_with_additional_scores(self, mock_parse, mock_client, sample_dialogue, mock_audio_path):
        """测试包含额外评分字段"""
        mock_gemini_response = {
            "score": 2,
            "student_answer": "I like pizza",
            "feedback": "很好",
            "fluency_score": 8.5,
            "pronunciation_score": 9.0,
            "confidence_score": 7.5
        }
        mock_parse.return_value = mock_gemini_response

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "response"

        score, result = evaluate_part3_single_question(mock_audio_path, sample_dialogue, 1)

        assert result["fluency_score"] == 8.5
        assert result["pronunciation_score"] == 9.0
        assert result["confidence_score"] == 7.5

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    def test_evaluate_single_question_missing_score(self, mock_parse, mock_client, sample_dialogue, mock_audio_path):
        """测试返回结果缺少 score 字段"""
        mock_gemini_response = {"student_answer": "Some answer", "feedback": "No score"}
        mock_parse.return_value = mock_gemini_response

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "response"

        score, result = evaluate_part3_single_question(mock_audio_path, sample_dialogue, 1)

        # 应该默认返回 0
        assert score == 0


class TestEvaluatePart3Group:
    """测试 evaluate_part3_group 函数"""

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    def test_evaluate_group_six_questions(self, mock_parse, mock_client, sample_dialogues_part3, mock_audio_path):
        """测试评估6个问题"""
        mock_response = {
            "questions": [
                {"question_num": 1, "score": 2, "student_answer": "Ans 1", "feedback": "好"},
                {"question_num": 2, "score": 1, "student_answer": "Ans 2", "feedback": "一般"},
                {"question_num": 3, "score": 2, "student_answer": "Ans 3", "feedback": "好"},
                {"question_num": 4, "score": 0, "student_answer": "", "feedback": "无回答"},
                {"question_num": 5, "score": 2, "student_answer": "Ans 5", "feedback": "好"},
                {"question_num": 6, "score": 1, "student_answer": "Ans 6", "feedback": "一般"},
            ],
            "fluency_score": 8.0,
            "pronunciation_score": 7.5,
            "confidence_score": 8.5
        }
        mock_parse.return_value = mock_response

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "response"

        total_score, results = evaluate_part3_group(mock_audio_path, sample_dialogues_part3, 1)

        assert total_score == 8  # 2+1+2+0+2+1
        assert len(results) == 6
        assert results[0]["score"] == 2
        assert results[3]["score"] == 0

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    def test_evaluate_group_with_start_question_7(self, mock_parse, mock_client, sample_dialogues_part3, mock_audio_path):
        """测试起始问题编号为7"""
        mock_response = {
            "questions": [
                {"question_num": i, "score": 2, "student_answer": f"Ans {i}", "feedback": "好"}
                for i in range(7, 13)
            ],
            "fluency_score": 8.0,
            "pronunciation_score": 7.5,
            "confidence_score": 8.5
        }
        mock_parse.return_value = mock_response

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "response"

        total_score, results = evaluate_part3_group(mock_audio_path, sample_dialogues_part3, 7)

        assert total_score == 12
        assert len(results) == 6
        assert results[0]["question_num"] == 7
        assert results[5]["question_num"] == 12

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    def test_evaluate_group_incomplete_results(self, mock_parse, mock_client, sample_dialogues_part3, mock_audio_path):
        """测试返回结果不完整时补充默认值"""
        # 只返回3个问题结果
        mock_response = {
            "questions": [
                {"question_num": 1, "score": 2, "student_answer": "Ans 1", "feedback": "好"},
                {"question_num": 2, "score": 1, "student_answer": "Ans 2", "feedback": "一般"},
                {"question_num": 3, "score": 2, "student_answer": "Ans 3", "feedback": "好"},
            ],
            "fluency_score": 7.0,
            "pronunciation_score": 7.0,
            "confidence_score": 7.0
        }
        mock_parse.return_value = mock_response

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "response"

        total_score, results = evaluate_part3_group(mock_audio_path, sample_dialogues_part3, 1)

        # 应该补充到6个问题
        assert len(results) == 6
        # 前3个是真实结果
        assert results[0]["score"] == 2
        assert results[1]["score"] == 1
        assert results[2]["score"] == 2
        # 后3个是默认值
        assert results[3]["score"] == 0
        assert results[3]["feedback"] == "未能识别回答"
        assert results[4]["score"] == 0
        assert results[5]["score"] == 0

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    def test_evaluate_group_overall_scores_added(self, mock_parse, mock_client, sample_dialogues_part3, mock_audio_path):
        """测试整体评分被添加到每个问题结果"""
        mock_response = {
            "questions": [
                {"question_num": i, "score": 2, "student_answer": f"Ans {i}", "feedback": "好"}
                for i in range(1, 7)
            ],
            "fluency_score": 8.5,
            "pronunciation_score": 9.0,
            "confidence_score": 7.5
        }
        mock_parse.return_value = mock_response

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "response"

        total_score, results = evaluate_part3_group(mock_audio_path, sample_dialogues_part3, 1)

        # 验证每个问题都包含整体评分
        for result in results:
            assert result["fluency_score"] == 8.5
            assert result["pronunciation_score"] == 9.0
            assert result["confidence_score"] == 7.5

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    def test_evaluate_group_default_overall_scores(self, mock_parse, mock_client, sample_dialogues_part3, mock_audio_path):
        """测试默认整体评分"""
        mock_response = {
            "questions": [
                {"question_num": i, "score": 2, "student_answer": f"Ans {i}", "feedback": "好"}
                for i in range(1, 7)
            ]
            # 缺少整体评分
        }
        mock_parse.return_value = mock_response

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "response"

        total_score, results = evaluate_part3_group(mock_audio_path, sample_dialogues_part3, 1)

        # 验证默认值为 7.0
        for result in results:
            assert result["fluency_score"] == 7.0
            assert result["pronunciation_score"] == 7.0
            assert result["confidence_score"] == 7.0


class TestEvaluatePart2All:
    """测试 evaluate_part2_all 函数"""

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    def test_evaluate_part2_twelve_questions(self, mock_parse, mock_client, sample_dialogues_part2, mock_audio_path):
        """测试评估12个Part 2问题"""
        mock_response = {
            "questions": [
                {"question_num": i, "score": 2, "student_answer": f"Ans {i}", "feedback": "好"}
                for i in range(1, 13)
            ],
            "fluency_score": 8.0,
            "pronunciation_score": 7.5,
            "confidence_score": 8.5
        }
        mock_parse.return_value = mock_response

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "response"

        total_score, results, overall_scores = evaluate_part2_all(mock_audio_path, sample_dialogues_part2)

        assert total_score == 24  # 12个问题，每个2分
        assert len(results) == 12
        assert overall_scores["fluency_score"] == 8.0
        assert overall_scores["pronunciation_score"] == 7.5
        assert overall_scores["confidence_score"] == 8.5

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    def test_evaluate_part2_incomplete_results(self, mock_parse, mock_client, sample_dialogues_part2, mock_audio_path):
        """测试Part 2返回结果不完整时补充默认值"""
        # 只返回8个问题结果
        mock_response = {
            "questions": [
                {"question_num": i, "score": 2, "student_answer": f"Ans {i}", "feedback": "好"}
                for i in range(1, 9)
            ],
            "fluency_score": 7.0,
            "pronunciation_score": 7.0,
            "confidence_score": 7.0
        }
        mock_parse.return_value = mock_response

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "response"

        total_score, results, overall_scores = evaluate_part2_all(mock_audio_path, sample_dialogues_part2)

        # 应该补充到12个问题
        assert len(results) == 12
        # 前8个是真实结果
        assert results[7]["score"] == 2
        # 后4个是默认值
        assert results[8]["score"] == 0
        assert results[8]["feedback"] == "未能识别回答"
        assert results[11]["score"] == 0

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    def test_evaluate_part2_returns_overall_scores(self, mock_parse, mock_client, sample_dialogues_part2, mock_audio_path):
        """测试Part 2返回整体评分"""
        mock_response = {
            "questions": [
                {"question_num": i, "score": 1, "student_answer": f"Ans {i}", "feedback": "一般"}
                for i in range(1, 13)
            ],
            "fluency_score": 9.0,
            "pronunciation_score": 8.5,
            "confidence_score": 9.5
        }
        mock_parse.return_value = mock_response

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "response"

        total_score, results, overall_scores = evaluate_part2_all(mock_audio_path, sample_dialogues_part2)

        assert total_score == 12
        assert overall_scores["fluency_score"] == 9.0
        assert overall_scores["pronunciation_score"] == 8.5
        assert overall_scores["confidence_score"] == 9.5

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    def test_evaluate_part2_mixed_scores(self, mock_parse, mock_client, sample_dialogues_part2, mock_audio_path):
        """测试Part 2混合得分"""
        mock_response = {
            "questions": [
                {"question_num": i, "score": 2 if i % 2 == 0 else 1, "student_answer": f"Ans {i}", "feedback": "好"}
                for i in range(1, 13)
            ],
            "fluency_score": 7.5,
            "pronunciation_score": 7.5,
            "confidence_score": 7.5
        }
        mock_parse.return_value = mock_response

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "response"

        total_score, results, overall_scores = evaluate_part2_all(mock_audio_path, sample_dialogues_part2)

        # 6个2分，6个1分 = 18分
        assert total_score == 18


class TestPromptGeneration:
    """测试 Prompt 生成"""

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    def test_single_question_prompt_contains_question_num(self, mock_parse, mock_client, sample_dialogue, mock_audio_path):
        """测试单个问题prompt包含问题编号"""
        mock_parse.return_value = {"score": 2, "student_answer": "Ans", "feedback": "好"}

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "response"

        evaluate_part3_single_question(mock_audio_path, sample_dialogue, 5)

        # 验证调用时的prompt包含问题编号
        call_args = mock_client_instance.analyze_audio_from_path.call_args
        prompt = call_args[0][1]
        assert "问题 5" in prompt

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    def test_group_prompt_contains_all_questions(self, mock_parse, mock_client, sample_dialogues_part3, mock_audio_path):
        """测试组评估prompt包含所有问题"""
        mock_parse.return_value = {
            "questions": [
                {"question_num": i, "score": 2, "student_answer": f"Ans {i}", "feedback": "好"}
                for i in range(1, 7)
            ],
            "fluency_score": 7.0,
            "pronunciation_score": 7.0,
            "confidence_score": 7.0
        }

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "response"

        evaluate_part3_group(mock_audio_path, sample_dialogues_part3, 1)

        call_args = mock_client_instance.analyze_audio_from_path.call_args
        prompt = call_args[0][1]
        # 验证包含所有6个问题
        for i in range(1, 7):
            assert f"问题 {i}" in prompt

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    def test_part2_prompt_contains_twelve_questions(self, mock_parse, mock_client, sample_dialogues_part2, mock_audio_path):
        """测试Part 2 prompt包含12个问题"""
        mock_parse.return_value = {
            "questions": [
                {"question_num": i, "score": 1, "student_answer": f"Ans {i}", "feedback": "好"}
                for i in range(1, 13)
            ],
            "fluency_score": 7.0,
            "pronunciation_score": 7.0,
            "confidence_score": 7.0
        }

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "response"

        evaluate_part2_all(mock_audio_path, sample_dialogues_part2)

        call_args = mock_client_instance.analyze_audio_from_path.call_args
        prompt = call_args[0][1]
        # 验证包含所有12个问题
        for i in range(1, 13):
            assert f"问题 {i}" in prompt


class TestRetryBehavior:
    """测试重试行为"""

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    @patch("services.part3_evaluator.time.sleep")
    def test_single_question_retry_on_failure(self, mock_sleep, mock_parse, mock_client, sample_dialogue, mock_audio_path):
        """测试单个问题评估失败重试"""
        # 前两次失败，第三次成功
        mock_parse.side_effect = [
            Exception("Parse error"),
            Exception("Parse error"),
            {"score": 2, "student_answer": "Ans", "feedback": "好"}
        ]

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "response"

        score, result = evaluate_part3_single_question(mock_audio_path, sample_dialogue, 1)

        assert score == 2
        assert mock_parse.call_count == 3

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    @patch("services.part3_evaluator.time.sleep")
    def test_group_retry_on_failure(self, mock_sleep, mock_parse, mock_client, sample_dialogues_part3, mock_audio_path):
        """测试组评估失败重试"""
        mock_parse.side_effect = [
            Exception("API error"),
            {
                "questions": [
                    {"question_num": i, "score": 2, "student_answer": f"Ans {i}", "feedback": "好"}
                    for i in range(1, 7)
                ],
                "fluency_score": 7.0,
                "pronunciation_score": 7.0,
                "confidence_score": 7.0
            }
        ]

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "response"

        total_score, results = evaluate_part3_group(mock_audio_path, sample_dialogues_part3, 1)

        assert total_score == 12
        assert mock_parse.call_count == 2


class TestEdgeCases:
    """测试边界情况"""

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    def test_empty_dialogue_student_options(self, mock_parse, mock_client, mock_audio_path):
        """测试空的学生选项"""
        empty_dialogue = {
            "teacher": "Test question",
            "student_options": []
        }

        mock_parse.return_value = {"score": 0, "student_answer": "", "feedback": "无回答"}

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "response"

        score, result = evaluate_part3_single_question(mock_audio_path, empty_dialogue, 1)

        assert score == 0

    @patch("services.part3_evaluator.GeminiClient")
    @patch("services.part3_evaluator.parse_gemini_response")
    def test_dialogue_missing_student_options(self, mock_parse, mock_client, mock_audio_path):
        """测试对话缺少student_options字段"""
        no_options_dialogue = {
            "teacher": "Test question"
        }

        mock_parse.return_value = {"score": 1, "student_answer": "Something", "feedback": "一般"}

        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.analyze_audio_from_path.return_value = "response"

        score, result = evaluate_part3_single_question(mock_audio_path, no_options_dialogue, 1)

        # get() 返回空列表，应该能处理
        assert score == 1
