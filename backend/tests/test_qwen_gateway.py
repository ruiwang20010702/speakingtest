"""
Tests for Qwen Gateway using respx for httpx mocking
Covers: Part 1/2 evaluation, summary analysis, report interpretation
"""
import pytest
import json
import respx
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from src.adapters.gateways.qwen_client import (
    QwenOmniGateway,
    Part1EvaluationResult,
    Part2EvaluationResult,
    SummaryAnalysisResult,
    ReportInterpretationResult
)


@pytest.fixture
def gateway():
    """Create Qwen gateway instance."""
    return QwenOmniGateway()


class TestQwenOmniGatewayPart1:
    """Tests for Part 1 evaluation using respx."""

    @pytest.mark.asyncio
    async def test_evaluate_part1_success(self, gateway):
        """Test successful Part 1 evaluation."""
        mock_content = json.dumps({
            "total_score": 85,
            "accuracy_score": 90,
            "fluency_score": 80,
            "pronunciation_score": 85,
            "integrity_score": 88,
            "part1_overall_suggestion": ["Great pronunciation!"],
            "details": [
                {"content": "Hello", "score": 95, "issue": None}
            ]
        })
        
        # Mock response object
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        
        async def mock_aiter_lines():
            yield f"data: {json.dumps({'choices': [{'delta': {'content': mock_content}}], 'usage': {'prompt_tokens': 100, 'completion_tokens': 50}})}"
            yield "data: [DONE]"
            
        mock_response.aiter_lines = MagicMock(return_value=mock_aiter_lines())

        # Mock stream context manager
        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__.return_value = mock_response
        mock_stream_ctx.__aexit__.return_value = None

        # Mock client context manager
        mock_client = AsyncMock()
        # client.stream returns an async context manager, so we mock it as a MagicMock (sync) that returns the ctx
        mock_client.stream = MagicMock(return_value=mock_stream_ctx)
        
        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__.return_value = mock_client
        mock_client_ctx.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client_ctx):
            result = await gateway.evaluate_part1_reading(
                audio_data=b"fake audio",
                reference_text="Hello, world!",
                audio_format="mp3"
            )

        assert result.success is True
        assert result.total_score == 85
        assert result.accuracy_score == 90

    @pytest.mark.asyncio
    @respx.mock
    async def test_evaluate_part1_json_error(self, gateway):
        """Test Part 1 evaluation with invalid JSON response."""
        mock_response = {
            "choices": [{
                "message": {
                    "content": "Invalid JSON content"
                }
            }],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50}
        }

        respx.post(url__regex=r".*/chat/completions").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        
        result = await gateway.evaluate_part1_reading(
            audio_data=b"fake audio",
            reference_text="Test",
            audio_format="mp3"
        )

        assert result.success is False
        assert "JSON" in result.error or "解析" in result.error


class TestQwenOmniGatewayPart2:
    """Tests for Part 2 evaluation using respx."""

    @pytest.mark.asyncio
    async def test_evaluate_part2_success(self, gateway):
        """Test successful Part 2 evaluation."""
        mock_content = json.dumps({
            "total_score": 75,
            "fluency_score": 80,
            "pronunciation_score": 70,
            "confidence_score": 75,
            "vocabulary_score": 72,
            "sentence_score": 78,
            "items": [
                {"no": 1, "transcript": "Answer", "score": "S", "feedback": "Good"},
                {"no": 2, "transcript": "Answer 2", "score": "A", "feedback": "OK"}
            ],
            "part2_overall_suggestion": ["Keep practicing!"]
        })
        
        # Mock response object
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        
        async def mock_aiter_lines():
            yield f"data: {json.dumps({'choices': [{'delta': {'content': mock_content}}], 'usage': {'prompt_tokens': 200, 'completion_tokens': 100}})}"
            yield "data: [DONE]"
            
        mock_response.aiter_lines = MagicMock(return_value=mock_aiter_lines())

        # Mock stream context manager
        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__.return_value = mock_response
        mock_stream_ctx.__aexit__.return_value = None

        # Mock client context manager
        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_stream_ctx)
        
        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__.return_value = mock_client
        mock_client_ctx.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client_ctx):
            result = await gateway.evaluate_part2(
                audio_data=b"fake audio",
                audio_format="mp3",
                questions=[{"no": 1, "question": "What is your name?"}]
            )

        assert result.success is True
        assert result.total_score == 75
        assert len(result.items) == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_evaluate_part2_api_error(self, gateway):
        """Test Part 2 evaluation with API error."""
        respx.post(url__regex=r".*/chat/completions").mock(
            side_effect=httpx.ConnectError("API connection failed")
        )

        result = await gateway.evaluate_part2(
            audio_data=b"fake audio",
            audio_format="mp3",
            questions=[]
        )

        assert result.success is False
        assert result.error is not None


class TestQwenOmniGatewaySummaryAnalysis:
    """Tests for summary analysis generation using respx."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_generate_summary_success(self, gateway):
        """Test successful summary analysis generation."""
        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "highlights": ["Good pronunciation", "Confident speaker"],
                        "weaknesses": ["Needs vocabulary improvement"],
                        "weekly_plan": ["Day 1: Practice words", "Day 2: Read aloud"],
                        "dimension_feedback": {
                            "fluency": {"comment": "Good flow", "tags": ["natural"]}
                        }
                    })
                }
            }],
            "usage": {"prompt_tokens": 150, "completion_tokens": 100}
        }

        respx.post(url__regex=r".*/chat/completions").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await gateway.generate_summary_analysis(
            student_name="小明",
            level="L2",
            total_score=85.0,
            star_level=4,
            radar_scores={"fluency": 80},
            part1_score=80.0,
            part2_score=90.0
        )

        assert result.success is True
        assert len(result.highlights) == 2
        assert len(result.weekly_plan) == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_generate_summary_json_error(self, gateway):
        """Test summary analysis with JSON parse error."""
        mock_response = {
            "choices": [{
                "message": {
                    "content": "Not valid JSON"
                }
            }],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50}
        }

        respx.post(url__regex=r".*/chat/completions").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await gateway.generate_summary_analysis(
            student_name="小明",
            level="L2",
            total_score=85.0,
            star_level=4,
            radar_scores={},
            part1_score=80.0,
            part2_score=90.0
        )

        assert result.success is False
        assert "JSON" in result.error


class TestQwenOmniGatewayInterpretation:
    """Tests for report interpretation generation using respx."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_generate_interpretation_success(self, gateway):
        """Test successful report interpretation generation."""
        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "pages": {
                            "cover": "Welcome page content",
                            "radar": "Radar analysis content",
                            "vocab": "Vocabulary page content",
                            "dialogue": "Dialogue page content",
                            "roadmap": "Learning roadmap content",
                            "badge": "Badge page content"
                        },
                        "full_script": "Complete teacher script for 10 minutes..."
                    })
                }
            }],
            "usage": {"prompt_tokens": 300, "completion_tokens": 500, "total_tokens": 800}
        }

        respx.post(url__regex=r".*/chat/completions").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await gateway.generate_report_interpretation(
            student_name="小明",
            level="L2",
            total_score=85.0,
            part1_score=80.0,
            part2_score=90.0,
            star_level=4
        )

        assert result.success is True
        assert result.pages is not None
        assert len(result.pages) == 6
        assert result.full_script is not None

    @pytest.mark.asyncio
    @respx.mock
    async def test_generate_interpretation_timeout(self, gateway):
        """Test interpretation generation with timeout."""
        respx.post(url__regex=r".*/chat/completions").mock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        result = await gateway.generate_report_interpretation(
            student_name="小明",
            level="L2",
            total_score=85.0,
            part1_score=80.0,
            part2_score=90.0,
            star_level=4
        )

        assert result.success is False
        assert result.error is not None


class TestQwenOmniGatewayEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_empty_audio_data(self, gateway):
        """Test with empty audio data."""
        mock_response = {
            "choices": [{"message": {"content": "{}"}}],
            "usage": {}
        }

        respx.post(url__regex=r".*/chat/completions").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        # Should not crash with empty data
        result = await gateway.evaluate_part1_reading(
            audio_data=b"",
            reference_text="Test",
            audio_format="mp3"
        )
        # Result may fail but should not throw exception

    @pytest.mark.asyncio
    async def test_thinking_tags_stripped(self, gateway):
        """Test that thinking tags are stripped from response."""
        mock_content = '<think>Internal reasoning...</think>{"total_score": 80}'
        
        # Mock response object
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        
        async def mock_aiter_lines():
            yield f"data: {json.dumps({'choices': [{'delta': {'content': mock_content}}], 'usage': {'prompt_tokens': 100, 'completion_tokens': 50}})}"
            yield "data: [DONE]"
            
        mock_response.aiter_lines = MagicMock(return_value=mock_aiter_lines())

        # Mock stream context manager
        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__.return_value = mock_response
        mock_stream_ctx.__aexit__.return_value = None

        # Mock client context manager
        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_stream_ctx)
        
        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__.return_value = mock_client
        mock_client_ctx.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client_ctx):
            result = await gateway.evaluate_part1_reading(
                audio_data=b"audio",
                reference_text="Test",
                audio_format="mp3"
            )

        # Should parse correctly after stripping thinking tags
        assert result.total_score == 80

    @pytest.mark.asyncio
    @respx.mock
    async def test_api_rate_limit_error(self, gateway):
        """Test handling of API rate limit (429) error."""
        respx.post(url__regex=r".*/chat/completions").mock(
            return_value=httpx.Response(429, json={"error": "Rate limit exceeded"})
        )

        result = await gateway.evaluate_part1_reading(
            audio_data=b"audio",
            reference_text="Test",
            audio_format="mp3"
        )

        assert result.success is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_server_error(self, gateway):
        """Test handling of server error (500)."""
        respx.post(url__regex=r".*/chat/completions").mock(
            return_value=httpx.Response(500, json={"error": "Internal server error"})
        )

        result = await gateway.evaluate_part2(
            audio_data=b"audio",
            audio_format="mp3",
            questions=[]
        )

        assert result.success is False
