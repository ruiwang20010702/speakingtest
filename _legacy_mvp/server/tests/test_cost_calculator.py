"""
测试成本计算服务
"""
import pytest
from services.cost_calculator import estimate_tokens, calculate_cost


class TestEstimateTokens:
    """测试 Token 估算"""

    def test_estimate_tokens_with_text_only(self):
        """测试仅文本的 token 估算"""
        text = "This is a test prompt with multiple words."
        tokens = estimate_tokens(text, audio_bytes=0)

        assert tokens["input_tokens"] > 0
        assert tokens["output_tokens"] > 0
        assert tokens["total_tokens"] > 0

    def test_estimate_tokens_with_audio(self):
        """测试带音频的 token 估算"""
        text = "Analyze this audio."
        audio_bytes = 1024 * 100  # 100KB
        tokens = estimate_tokens(text, audio_bytes)

        # 音频应该增加 input_tokens
        assert tokens["input_tokens"] > len(text.split()) * 2
        assert tokens["output_tokens"] > 0

    def test_estimate_tokens_large_audio(self):
        """测试大音频文件的 token 估算"""
        audio_bytes = 1024 * 1024  # 1MB
        tokens = estimate_tokens("", audio_bytes)

        # 1MB 音频大约需要更多 tokens
        assert tokens["input_tokens"] > 1000


class TestCalculateCost:
    """测试成本计算"""

    def test_calculate_cost_text_only(self):
        """测试仅文本的成本计算"""
        cost = calculate_cost(text_tokens=1000, audio_tokens=0, output_tokens=500)

        assert cost > 0
        assert cost < 1  # 应该很小

    def test_calculate_cost_with_audio(self):
        """测试带音频的成本计算"""
        cost = calculate_cost(text_tokens=5000, audio_tokens=10000, output_tokens=1000)

        assert cost > 0
        # 音频 token 更贵，所以成本应该更高
        cost_text_only = calculate_cost(text_tokens=5000, audio_tokens=0, output_tokens=1000)
        assert cost > cost_text_only

    def test_calculate_cost_large_values(self):
        """测试大量 tokens 的成本计算"""
        cost = calculate_cost(
            text_tokens=100000,
            audio_tokens=500000,
            output_tokens=50000
        )

        # 大量 tokens 应该产生明显成本 (约 $0.655)
        assert cost > 0.5
