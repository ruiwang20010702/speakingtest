"""
Tests for Part 1 Evaluation Use Case
Covers: SubmitPart1UseCase, ProcessPart1TaskUseCase, EvaluatePart1UseCase
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from src.use_cases.evaluate_part1 import (
    EvaluatePart1UseCase, Part1EvaluationRequest, Part1EvaluationResponse,
    SubmitPart1UseCase, SubmitPart1Request, SubmitPart1Response,
    ProcessPart1TaskUseCase
)
from src.infrastructure.queue_service import Part1Task
from src.adapters.repositories.models import TestModel, StudentProfileModel
from src.adapters.gateways.qwen_client import Part1EvaluationResult


class TestSubmitPart1UseCase:
    """Tests for Part 1 async task submission."""

    @pytest.mark.asyncio
    async def test_submit_success(self, test_db, student_profile):
        """Test successful Part 1 submission."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="pending"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        request = SubmitPart1Request(
            test_id=test.id,
            audio_url="https://oss.example.com/part1.mp3",
            reference_text="Hello, how are you?"
        )

        with patch("src.use_cases.evaluate_part1.enqueue_part1_task", new_callable=AsyncMock) as mock_enqueue:
            use_case = SubmitPart1UseCase(test_db)
            response = await use_case.execute(request)

            assert response.success is True
            assert response.task_id is not None
            mock_enqueue.assert_called_once()

        await test_db.refresh(test)
        assert test.status == "part1_processing"
        assert test.part1_audio_url == "https://oss.example.com/part1.mp3"

    @pytest.mark.asyncio
    async def test_submit_fails_invalid_status(self, test_db, student_profile):
        """Test submission fails when status is not pending."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="part1_done"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        request = SubmitPart1Request(
            test_id=test.id,
            audio_url="https://oss.example.com/part1.mp3",
            reference_text="Hello"
        )

        use_case = SubmitPart1UseCase(test_db)
        response = await use_case.execute(request)

        assert response.success is False
        assert "part1_done" in response.message

    @pytest.mark.asyncio
    async def test_submit_fails_test_not_found(self, test_db):
        """Test submission fails when test doesn't exist."""
        request = SubmitPart1Request(
            test_id=99999,
            audio_url="https://oss.example.com/audio.mp3",
            reference_text="Test"
        )

        use_case = SubmitPart1UseCase(test_db)
        response = await use_case.execute(request)

        assert response.success is False
        assert "不存在" in response.message

    @pytest.mark.asyncio
    async def test_submit_saves_url_even_on_status_failure(self, test_db, student_profile):
        """Test audio URL is saved even when status check fails."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        request = SubmitPart1Request(
            test_id=test.id,
            audio_url="https://oss.example.com/saved.mp3",
            reference_text="Test"
        )

        use_case = SubmitPart1UseCase(test_db)
        response = await use_case.execute(request)

        assert response.success is False
        await test_db.refresh(test)
        assert test.part1_audio_url == "https://oss.example.com/saved.mp3"


class TestProcessPart1TaskUseCase:
    """Tests for Part 1 task processing (worker)."""

    @pytest.fixture
    def mock_qwen_gateway(self):
        """Create mock Qwen gateway."""
        gateway = MagicMock()
        gateway.evaluate_part1_reading = AsyncMock()
        return gateway

    @pytest.fixture
    def sample_qwen_result(self):
        """Sample successful Part 1 evaluation result."""
        result = MagicMock(spec=Part1EvaluationResult)
        result.success = True
        result.total_score = 85.0
        result.accuracy_score = 90.0
        result.fluency_score = 80.0
        result.pronunciation_score = 85.0
        result.integrity_score = 82.0
        result.part1_overall_suggestion = ["Practice more"]
        result.usage = {"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80}
        result.to_dict = MagicMock(return_value={"total_score": 85.0})
        return result

    @pytest.mark.asyncio
    async def test_process_success(self, test_db, student_profile, mock_qwen_gateway, sample_qwen_result):
        """Test successful Part 1 processing."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="part1_processing"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        task = Part1Task(
            task_id="test-task",
            test_id=test.id,
            audio_url="https://oss.example.com/audio.mp3",
            reference_text="Hello, how are you?"
        )

        mock_qwen_gateway.evaluate_part1_reading.return_value = sample_qwen_result

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.content = b"audio data"
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            use_case = ProcessPart1TaskUseCase(test_db, mock_qwen_gateway)
            result = await use_case.execute(task)

            assert result is True

        await test_db.refresh(test)
        assert test.status == "part1_done"
        assert test.part1_score == Decimal("85.0")

    @pytest.mark.asyncio
    async def test_process_fails_audio_download(self, test_db, student_profile, mock_qwen_gateway):
        """Test processing fails when audio download fails."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="part1_processing",
            retry_count=0
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        task = Part1Task(
            task_id="test-task",
            test_id=test.id,
            audio_url="https://invalid.example.com/audio.mp3",
            reference_text="Test"
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Network error")
            )

            use_case = ProcessPart1TaskUseCase(test_db, mock_qwen_gateway)
            result = await use_case.execute(task)

            assert result is False

        await test_db.refresh(test)
        assert test.status == "failed"
        assert test.retry_count == 1

    @pytest.mark.asyncio
    async def test_process_fails_qwen_error(self, test_db, student_profile, mock_qwen_gateway):
        """Test processing fails when Qwen API fails."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="part1_processing",
            retry_count=0
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        task = Part1Task(
            task_id="test-task",
            test_id=test.id,
            audio_url="https://oss.example.com/audio.mp3",
            reference_text="Test"
        )

        mock_qwen_gateway.evaluate_part1_reading.return_value = MagicMock(
            success=False, error="API error"
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.content = b"audio data"
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            use_case = ProcessPart1TaskUseCase(test_db, mock_qwen_gateway)
            result = await use_case.execute(task)

            assert result is False

        await test_db.refresh(test)
        assert test.status == "failed"


class TestEvaluatePart1UseCase:
    """Tests for synchronous Part 1 evaluation."""

    @pytest.fixture
    def mock_qwen_gateway(self):
        """Create mock Qwen gateway."""
        gateway = MagicMock()
        gateway.evaluate_part1_reading = AsyncMock()
        return gateway

    @pytest.mark.asyncio
    async def test_evaluate_success(self, test_db, student_profile, mock_qwen_gateway):
        """Test successful synchronous Part 1 evaluation."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="pending"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        request = Part1EvaluationRequest(
            test_id=test.id,
            reference_text="Hello, world!",
            audio_data=b"fake audio data"
        )

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.total_score = 90.0
        mock_result.accuracy_score = 95.0
        mock_result.fluency_score = 85.0
        mock_result.pronunciation_score = 88.0
        mock_result.integrity_score = 92.0
        mock_result.part1_overall_suggestion = ["Great job!"]
        mock_result.usage = {"prompt_tokens": 100, "completion_tokens": 50}
        mock_result.to_dict = MagicMock(return_value={})

        mock_qwen_gateway.evaluate_part1_reading.return_value = mock_result

        with patch("src.use_cases.evaluate_part1.upload_test_audio", new_callable=AsyncMock) as mock_upload:
            mock_upload.return_value = MagicMock(success=True, url="https://oss.example.com/test.pcm")

            use_case = EvaluatePart1UseCase(test_db, mock_qwen_gateway)
            response = await use_case.execute(request)

            assert response.success is True
            assert response.score == 90.0
            assert response.audio_url == "https://oss.example.com/test.pcm"

        await test_db.refresh(test)
        assert test.status == "part1_done"

    @pytest.mark.asyncio
    async def test_evaluate_fails_test_not_found(self, test_db, mock_qwen_gateway):
        """Test evaluation fails when test doesn't exist."""
        request = Part1EvaluationRequest(
            test_id=99999,
            reference_text="Test",
            audio_data=b"audio"
        )

        use_case = EvaluatePart1UseCase(test_db, mock_qwen_gateway)
        response = await use_case.execute(request)

        assert response.success is False
        assert "not found" in response.error

    @pytest.mark.asyncio
    async def test_evaluate_fails_invalid_status(self, test_db, student_profile, mock_qwen_gateway):
        """Test evaluation fails when status is invalid."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="processing"  # Invalid for Part 1
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        request = Part1EvaluationRequest(
            test_id=test.id,
            reference_text="Test",
            audio_data=b"audio"
        )

        use_case = EvaluatePart1UseCase(test_db, mock_qwen_gateway)
        response = await use_case.execute(request)

        assert response.success is False
        assert "Invalid test status" in response.error
