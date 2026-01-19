"""
Tests for Part 2 Evaluation Use Case
Covers: SubmitPart2UseCase, ProcessPart2TaskUseCase, star level calculation
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from src.use_cases.evaluate_part2 import (
    SubmitPart2UseCase, SubmitPart2Request, SubmitPart2Response,
    ProcessPart2TaskUseCase
)
from src.infrastructure.queue_service import Part2Task
from src.adapters.repositories.models import TestModel, TestItemModel, StudentProfileModel
from src.adapters.gateways.qwen_client import Part2EvaluationResult


class TestSubmitPart2UseCase:
    """Tests for Part 2 task submission."""

    @pytest.mark.asyncio
    async def test_submit_success_from_part1_done(self, test_db, student_profile):
        """Test successful submission when status is part1_done."""
        # Arrange
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="part1_done",
            part1_score=80.0
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        request = SubmitPart2Request(
            test_id=test.id,
            audio_url="https://oss.example.com/audio.mp3",
            questions=[{"no": 1, "question": "What is your name?"}]
        )

        with patch("src.use_cases.evaluate_part2.enqueue_part2_task", new_callable=AsyncMock) as mock_enqueue:
            use_case = SubmitPart2UseCase(test_db)
            response = await use_case.execute(request)

            assert response.success is True
            assert response.task_id is not None
            mock_enqueue.assert_called_once()

        # Verify status updated
        await test_db.refresh(test)
        assert test.status == "processing"
        assert test.part2_audio_url == "https://oss.example.com/audio.mp3"

    @pytest.mark.asyncio
    async def test_submit_success_from_part1_processing(self, test_db, student_profile):
        """Test submission when Part 1 is still processing."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="part1_processing"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        request = SubmitPart2Request(
            test_id=test.id,
            audio_url="https://oss.example.com/audio.mp3",
            questions=[]
        )

        with patch("src.use_cases.evaluate_part2.enqueue_part2_task", new_callable=AsyncMock):
            use_case = SubmitPart2UseCase(test_db)
            response = await use_case.execute(request)

            assert response.success is True

        # Status should remain part1_processing
        await test_db.refresh(test)
        assert test.status == "part1_processing"

    @pytest.mark.asyncio
    async def test_submit_fails_invalid_status(self, test_db, student_profile):
        """Test submission fails when status is not allowed."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed"  # Invalid for Part 2 submission
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        request = SubmitPart2Request(
            test_id=test.id,
            audio_url="https://oss.example.com/audio.mp3",
            questions=[]
        )

        use_case = SubmitPart2UseCase(test_db)
        response = await use_case.execute(request)

        assert response.success is False
        assert "completed" in response.message

    @pytest.mark.asyncio
    async def test_submit_fails_test_not_found(self, test_db):
        """Test submission fails when test doesn't exist."""
        request = SubmitPart2Request(
            test_id=99999,
            audio_url="https://oss.example.com/audio.mp3",
            questions=[]
        )

        use_case = SubmitPart2UseCase(test_db)
        response = await use_case.execute(request)

        assert response.success is False
        assert "不存在" in response.message

    @pytest.mark.asyncio
    async def test_submit_fails_enqueue_error(self, test_db, student_profile):
        """Test submission fails when queue is unavailable."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="part1_done"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        request = SubmitPart2Request(
            test_id=test.id,
            audio_url="https://oss.example.com/audio.mp3",
            questions=[]
        )

        with patch("src.use_cases.evaluate_part2.enqueue_part2_task", new_callable=AsyncMock) as mock_enqueue:
            mock_enqueue.side_effect = Exception("Queue connection failed")

            use_case = SubmitPart2UseCase(test_db)
            response = await use_case.execute(request)

            assert response.success is False
            assert "入队失败" in response.message


class TestProcessPart2TaskUseCase:
    """Tests for Part 2 task processing."""

    @pytest.fixture
    def mock_qwen_gateway(self):
        """Create mock Qwen gateway."""
        gateway = MagicMock()
        gateway.evaluate_part2 = AsyncMock()
        gateway.generate_summary_analysis = AsyncMock()
        return gateway

    @pytest.fixture
    def sample_qwen_result(self):
        """Sample successful Qwen evaluation result."""
        result = MagicMock(spec=Part2EvaluationResult)
        result.success = True
        result.total_score = 85.0
        result.transcript = "Student transcript..."
        result.items = [
            {"no": 1, "score": "S", "transcript": "Answer 1", "feedback": "Good"},
            {"no": 2, "score": "A", "transcript": "Answer 2", "feedback": "OK"},
        ]
        result.usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        result.to_dict = MagicMock(return_value={"total_score": 85.0})
        return result

    @pytest.mark.asyncio
    async def test_process_success(self, test_db, student_profile, mock_qwen_gateway, sample_qwen_result):
        """Test successful Part 2 processing."""
        # Create test in part1_done status
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="part1_done",
            part1_score=Decimal("80.0")
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        task = Part2Task(
            task_id="test-task",
            test_id=test.id,
            audio_url="https://oss.example.com/audio.mp3",
            questions=[{"no": 1, "question": "Test?"}]
        )

        mock_qwen_gateway.evaluate_part2.return_value = sample_qwen_result
        mock_qwen_gateway.generate_summary_analysis.return_value = MagicMock(
            success=True, highlights=[], weaknesses=[], weekly_plan=[], dimension_feedback=None, usage={}
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.content = b"audio data"
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            use_case = ProcessPart2TaskUseCase(test_db, mock_qwen_gateway)
            result = await use_case.execute(task)

            assert result is True

        # Verify test updated
        await test_db.refresh(test)
        assert test.status == "completed"
        assert test.part2_score == 85.0
        assert test.total_score == 82.5  # (80 + 85) / 2

    @pytest.mark.asyncio
    async def test_process_fails_audio_download(self, test_db, student_profile, mock_qwen_gateway):
        """Test processing fails when audio download fails."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="part1_done"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        task = Part2Task(
            task_id="test-task",
            test_id=test.id,
            audio_url="https://invalid.example.com/audio.mp3",
            questions=[]
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Network error")
            )

            use_case = ProcessPart2TaskUseCase(test_db, mock_qwen_gateway)
            result = await use_case.execute(task)

            assert result is False

        await test_db.refresh(test)
        assert test.status == "failed"
        assert "下载音频失败" in test.failure_reason

    @pytest.mark.asyncio
    async def test_process_fails_qwen_error(self, test_db, student_profile, mock_qwen_gateway):
        """Test processing fails when Qwen API fails."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="part1_done"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        task = Part2Task(
            task_id="test-task",
            test_id=test.id,
            audio_url="https://oss.example.com/audio.mp3",
            questions=[]
        )

        mock_qwen_gateway.evaluate_part2.return_value = MagicMock(
            success=False, error="API rate limit exceeded", usage={}
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.content = b"audio data"
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            use_case = ProcessPart2TaskUseCase(test_db, mock_qwen_gateway)
            result = await use_case.execute(task)

            assert result is False

        await test_db.refresh(test)
        assert test.status == "failed"

    @pytest.mark.xfail(reason="Complex async/mock interaction - needs deeper refactoring")
    @pytest.mark.asyncio
    async def test_process_waits_for_part1(self, test_db, student_profile, mock_qwen_gateway, sample_qwen_result):
        """Test processing waits when Part 1 is still processing."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="part1_processing"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        task = Part2Task(
            task_id="test-task",
            test_id=test.id,
            audio_url="https://oss.example.com/audio.mp3",
            questions=[]
        )

        # Simulate Part 1 completing after first check
        call_count = 0
        original_refresh = test_db.refresh

        async def mock_refresh(obj):
            nonlocal call_count
            await original_refresh(obj)
            call_count += 1
            if call_count >= 1:
                obj.status = "part1_done"
                obj.part1_score = Decimal("80.0")

        mock_qwen_gateway.evaluate_part2.return_value = sample_qwen_result
        mock_qwen_gateway.generate_summary_analysis.return_value = MagicMock(
            success=True, highlights=[], weaknesses=[], weekly_plan=[], dimension_feedback=None, usage={}
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.content = b"audio data"
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            with patch.object(test_db, 'refresh', mock_refresh):
                with patch("src.use_cases.evaluate_part2.asyncio.sleep", new_callable=AsyncMock):
                    use_case = ProcessPart2TaskUseCase(test_db, mock_qwen_gateway)
                    result = await use_case.execute(task)

                    assert result is True


class TestStarLevelCalculation:
    """Tests for star level calculation logic."""

    @pytest.mark.parametrize("total_score,expected_star", [
        (95, 5),
        (90, 5),
        (89, 4),
        (80, 4),
        (79, 3),
        (60, 3),
        (59, 2),
        (40, 2),
        (39, 1),
        (0, 1),
    ])
    def test_star_level_calculation(self, total_score, expected_star):
        """Test star level is calculated correctly for various scores."""
        use_case = ProcessPart2TaskUseCase.__new__(ProcessPart2TaskUseCase)
        result = use_case._calculate_star_level(total_score)
        assert result == expected_star
