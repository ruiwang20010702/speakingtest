"""
Tests for Report Interpretation Use Case
Covers: process_interpretation_task, cost recording
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from src.use_cases.evaluate_interpretation import (
    process_interpretation_task,
    _record_interpretation_cost,
    MAX_RETRIES
)
from src.infrastructure.queue_service import InterpretationTask
from src.adapters.repositories.models import TestModel


class TestProcessInterpretationTask:
    """Tests for interpretation task processing."""

    @pytest.fixture
    def sample_task(self):
        """Sample interpretation task."""
        return InterpretationTask(
            task_id="test-task-123",
            test_id=1,
            student_name="小明",
            level="L2",
            total_score=85.0,
            part1_score=80.0,
            part2_score=90.0,
            star_level=4,
            part1_details={"words": []},
            part2_items=[],
            radar_data=[]
        )

    @pytest.mark.asyncio
    async def test_process_success(self, test_db, student_profile, sample_task):
        """Test successful interpretation processing."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L2",
            unit="Unit 1",
            status="completed",
            total_score=Decimal("85.0"),
            interpretation_status="generating"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        sample_task.test_id = test.id

        mock_interpretation = MagicMock()
        mock_interpretation.success = True
        mock_interpretation.pages_to_json = MagicMock(return_value={"cover": "Content"})
        mock_interpretation.full_script = "Full script content..."
        mock_interpretation.usage = {"prompt_tokens": 100, "completion_tokens": 200}

        with patch("src.use_cases.evaluate_interpretation.async_session_factory") as mock_session:
            mock_session.return_value.__aenter__.return_value = test_db

            with patch("src.use_cases.evaluate_interpretation.QwenOmniGateway") as mock_gateway_class:
                mock_gateway = MagicMock()
                mock_gateway_class.return_value = mock_gateway

                with patch("src.adapters.controllers.report_controller.ReportInterpretationService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.generate = AsyncMock(return_value=mock_interpretation)
                    mock_service_class.return_value = mock_service

                    result = await process_interpretation_task(sample_task)
                    assert result is True

        await test_db.refresh(test)
        assert test.interpretation_status == "completed"
        assert test.interpretation_pages is not None

    @pytest.mark.asyncio
    async def test_process_fails_max_retries(self, test_db, student_profile, sample_task):
        """Test processing fails after max retries."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L2",
            unit="Unit 1",
            status="completed",
            interpretation_status="generating",
            interpretation_retry_count=MAX_RETRIES  # Already at max
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        sample_task.test_id = test.id

        with patch("src.use_cases.evaluate_interpretation.async_session_factory") as mock_session:
            mock_session.return_value.__aenter__.return_value = test_db

            result = await process_interpretation_task(sample_task)
            assert result is True  # Returns True to stop retrying

        await test_db.refresh(test)
        assert test.interpretation_status == "failed"

    @pytest.mark.asyncio
    async def test_process_test_not_found(self, test_db, sample_task):
        """Test processing when test doesn't exist."""
        sample_task.test_id = 99999

        with patch("src.use_cases.evaluate_interpretation.async_session_factory") as mock_session:
            mock_session.return_value.__aenter__.return_value = test_db

            result = await process_interpretation_task(sample_task)
            assert result is True  # Returns True to avoid infinite retry


class TestRecordInterpretationCost:
    """Tests for cost recording logic."""

    def test_record_cost_success(self):
        """Test cost is correctly recorded."""
        test = MagicMock()
        test.cost = Decimal("0.0")
        test.tokens_used = {}

        interpretation = MagicMock()
        interpretation.success = True
        interpretation.usage = {
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "total_tokens": 1500
        }

        _record_interpretation_cost(test, interpretation, attempt=1)

        # Verify cost calculation: (1000 * 0.0008 + 500 * 0.002) / 1000
        expected_cost = (1000 * 0.0008 / 1000) + (500 * 0.002 / 1000)
        assert float(test.cost) == pytest.approx(expected_cost, rel=1e-4)

        # Verify history recorded
        assert "interpretation_history" in test.tokens_used
        assert len(test.tokens_used["interpretation_history"]) == 1
        assert test.tokens_used["interpretation_history"][0]["attempt"] == 1

    def test_record_cost_no_usage(self):
        """Test no cost recorded when usage is None."""
        test = MagicMock()
        test.cost = Decimal("0.0")
        test.tokens_used = {}

        interpretation = MagicMock()
        interpretation.usage = None

        _record_interpretation_cost(test, interpretation, attempt=1)

        # No changes when no usage
        assert test.cost == Decimal("0.0")

    def test_record_cost_with_error(self):
        """Test error is recorded in history when failed."""
        test = MagicMock()
        test.cost = Decimal("0.0")
        test.tokens_used = {}

        interpretation = MagicMock()
        interpretation.success = False
        interpretation.error = "API timeout error"
        interpretation.usage = {"prompt_tokens": 100, "completion_tokens": 0, "total_tokens": 100}

        _record_interpretation_cost(test, interpretation, attempt=1)

        assert "interpretation_history" in test.tokens_used
        assert test.tokens_used["interpretation_history"][0]["success"] is False
        assert "error" in test.tokens_used["interpretation_history"][0]

    def test_record_cost_accumulates(self):
        """Test costs accumulate across multiple attempts."""
        test = MagicMock()
        test.cost = Decimal("0.001")  # Existing cost
        test.tokens_used = {
            "part1_history": [{"cost": 0.001}],
            "interpretation_history": []
        }

        interpretation = MagicMock()
        interpretation.success = True
        interpretation.usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

        _record_interpretation_cost(test, interpretation, attempt=1)

        # Verify total_cost includes all history
        assert test.tokens_used["total_cost"] > 0.001
