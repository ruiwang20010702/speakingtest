"""
测试 Gemini 评分服务
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from services.gemini_scorer import (
    calculate_star_rating,
    create_part1_prompt,
    create_part2_prompt,
    create_part3_prompt,
    parse_gemini_response
)


class TestCalculateStarRating:
    """测试星级评分计算"""

    def test_five_stars(self):
        """93%+ = 5星"""
        assert calculate_star_rating(41, 44) == 5  # 93.18%
        assert calculate_star_rating(44, 44) == 5  # 100%

    def test_four_stars(self):
        """80-92% = 4星"""
        assert calculate_star_rating(36, 44) == 4  # 81.81%
        assert calculate_star_rating(40, 44) == 4  # 90.90%

    def test_three_stars(self):
        """50-79% = 3星"""
        assert calculate_star_rating(22, 44) == 3  # 50%
        assert calculate_star_rating(30, 44) == 3  # 68.18%

    def test_two_stars(self):
        """1-49% = 2星"""
        assert calculate_star_rating(1, 44) == 2  # 2.27%
        assert calculate_star_rating(20, 44) == 2  # 45.45%

    def test_one_star(self):
        """0% = 1星"""
        assert calculate_star_rating(0, 44) == 1


class TestPromptCreation:
    """测试 Prompt 创建"""

    def test_create_part1_prompt(self):
        """测试 Part 1 prompt 创建"""
        words = ["apple", "banana", "cherry"]
        prompt = create_part1_prompt(words)

        assert "apple" in prompt
        assert "banana" in prompt
        assert "cherry" in prompt
        assert "3" in prompt  # 单词数量
        assert "3分" in prompt  # 总分
        assert "JSON" in prompt

    def test_create_part2_prompt(self):
        """测试 Part 2 prompt 创建"""
        words = ["cat", "dog"]
        sentences = ["The cat is black", "The dog is brown"]
        prompt = create_part2_prompt(words, sentences)

        assert "cat" in prompt
        assert "dog" in prompt
        assert "The cat is black" in prompt
        assert "The dog is brown" in prompt
        assert "JSON" in prompt

    def test_create_part3_prompt(self):
        """测试 Part 3 prompt 创建"""
        dialogues = [
            {"teacher": "What's your name?", "student_options": ["My name is Tom"]},
            {"teacher": "How old are you?", "student_options": ["I am ten years old"]}
        ]
        prompt = create_part3_prompt(dialogues)

        assert "What's your name?" in prompt
        assert "How old are you?" in prompt
        assert "24分" in prompt  # 总分
        assert "JSON" in prompt


class TestParseGeminiResponse:
    """测试 Gemini 响应解析"""

    def test_parse_clean_json(self):
        """测试解析干净的 JSON"""
        response = '{"score": 10, "correct_words": ["apple"], "incorrect_words": ["banana"]}'
        result = parse_gemini_response(response)

        assert result["score"] == 10
        assert result["correct_words"] == ["apple"]
        assert result["incorrect_words"] == ["banana"]

    def test_parse_json_in_code_block(self):
        """测试解析代码块中的 JSON"""
        response = '''```json
        {"score": 8, "correct_words": ["cat"], "incorrect_words": ["dog"]}
        ```'''
        result = parse_gemini_response(response)

        assert result["score"] == 8

    def test_parse_json_with_trailing_comma(self):
        """测试解析带尾随逗号的 JSON"""
        response = '{"score": 10, "correct_words": ["apple",],}'
        result = parse_gemini_response(response)

        assert result["score"] == 10

    def test_parse_invalid_json_raises_error(self):
        """测试无效 JSON 抛出错误"""
        with pytest.raises(Exception):
            parse_gemini_response("not a json")

    def test_parse_questions_format(self):
        """测试解析 questions 数组格式"""
        response = '{"questions": [{"score": 2}, {"score": 1}]}'
        result = parse_gemini_response(response)

        assert "questions" in result
