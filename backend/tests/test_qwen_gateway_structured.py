import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.adapters.gateways.qwen_client import QwenOmniGateway, SummaryAnalysisResult
import json

class TestQwenOmniGatewayStructured:
    @pytest.fixture
    def gateway(self):
        return QwenOmniGateway()

    @pytest.mark.asyncio
    async def test_generate_summary_analysis_success(self, gateway):
        """Test successful generation and parsing of summary analysis (qwen-plus structured)."""
        # Mock response from OpenAI client
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "highlights": ["发音清晰准确", "表达自信大胆"],
                        "weaknesses": ["部分长句停顿较多"],
                        "weekly_plan": ["第一天：复习 Unit 1 单词", "第二天：练习对话", "第三天：模拟测试"]
                    })
                )
            )
        ]
        # Simulate usage attribute being accessed (optional depending on implementation)
        # In current qwen_client.py, it expects a real dict in usage
        
        # Patch the httpx.AsyncClient.post instead since gateway uses httpx
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {
                    "choices": [{
                        "message": {
                            "content": json.dumps({
                                "highlights": ["发音清晰准确", "表达自信大胆"],
                                "weaknesses": ["部分长句停顿较多"],
                                "weekly_plan": ["第一天：复习 Unit 1 单词", "第二天：练习对话", "第三天：模拟测试"]
                            })
                        }
                    }],
                    "usage": {"total_tokens": 100}
                }
            )
            mock_post.return_value.raise_for_status = MagicMock()

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
            assert result.highlights == ["发音清晰准确", "表达自信大胆"]
            assert len(result.weekly_plan) == 3
            assert result.error is None

    @pytest.mark.asyncio
    async def test_generate_summary_analysis_parsing_error(self, gateway):
        """Test handling of invalid JSON in summary analysis response."""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {
                    "choices": [{
                        "message": {
                            "content": "Invalid JSON content"
                        }
                    }],
                    "usage": {"total_tokens": 100}
                }
            )
            mock_post.return_value.raise_for_status = MagicMock()

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
            assert result.highlights is None

    @pytest.mark.asyncio
    async def test_generate_report_interpretation_success(self, gateway):
        """Test successful generation of teacher report interpretation."""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {
                    "choices": [{
                        "message": {
                            "content": json.dumps({
                                "pages": {
                                    "cover": "Cover content",
                                    "radar": "Radar content",
                                    "vocab": "Vocab content",
                                    "dialogue": "Dialogue content",
                                    "roadmap": "Roadmap content",
                                    "badge": "Badge content"
                                },
                                "full_script": "Hi Parent, this is the full script..."
                            })
                        }
                    }],
                    "usage": {"total_tokens": 100}
                }
            )
            mock_post.return_value.raise_for_status = MagicMock()

            result = await gateway.generate_report_interpretation(
                student_name="小明",
                level="L2",
                total_score=85.0,
                part1_score=80.0,
                part2_score=90.0,
                star_level=4
            )
            
            assert result.success is True
            assert result.full_script == "Hi Parent, this is the full script..."
            assert result.pages["cover"] == "Cover content"
            assert len(result.pages) == 6
