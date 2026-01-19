"""
Tests for Test Controller
Covers: Part 1/2 submission, test status, full report
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from src.adapters.repositories.models import TestModel, TestItemModel, StudentProfileModel, QuestionModel


class TestGetTestStatus:
    """Tests for GET /tests/{test_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_status_success(self, test_db, student_profile, client, auth_teacher):
        """Test getting test status."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed",
            part1_score=Decimal("80.0"),
            part2_score=Decimal("85.0"),
            total_score=Decimal("82.5"),
            star_level=4
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        response = await client.get(f"/api/v1/tests/{test.id}")
        assert response.status_code == 200

        data = response.json()
        assert data["test_id"] == test.id
        assert data["status"] == "completed"
        assert data["part1_score"] == 80.0
        assert data["star_level"] == 4

    @pytest.mark.asyncio
    async def test_get_status_not_found(self, client, auth_teacher):
        """Test getting status of non-existent test."""
        response = await client.get("/api/v1/tests/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_status_pending(self, test_db, student_profile, client, auth_teacher):
        """Test getting status of pending test."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="pending"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        response = await client.get(f"/api/v1/tests/{test.id}")
        assert response.status_code == 200
        assert response.json()["status"] == "pending"


class TestGetFullReport:
    """Tests for GET /tests/{test_id}/report endpoint."""

    @pytest.mark.asyncio
    async def test_get_report_completed(self, test_db, student_profile, client, auth_teacher):
        """Test getting full report for completed test."""
        # Create completed test
        test = TestModel(
            student_id=student_profile.user_id,
            level="L2",
            unit="Unit 3",
            status="completed",
            part1_score=Decimal("85.0"),
            part2_score=Decimal("90.0"),
            total_score=Decimal("87.5"),
            star_level=4,
            part1_raw_result={
                "accuracy_score": 88.0,
                "fluency_score": 82.0,
                "pronunciation_score": 85.0,
                "integrity_score": 90.0,
                "part1_overall_suggestion": ["Great reading!"]
            },
            part2_raw_result={
                "fluency_score": 88.0,
                "pronunciation_score": 85.0,
                "confidence_score": 90.0,
                "vocabulary_score": 87.0,
                "sentence_score": 92.0,
                "part2_overall_suggestion": ["Keep practicing!"]
            },
            part2_transcript="Student transcript..."
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        # Add test items
        items = [
            TestItemModel(test_id=test.id, question_no=1, score=2, feedback="Excellent"),
            TestItemModel(test_id=test.id, question_no=2, score=1, feedback="Good")
        ]
        for item in items:
            test_db.add(item)
        await test_db.commit()

        response = await client.get(f"/api/v1/tests/{test.id}/report")
        assert response.status_code == 200

        data = response.json()
        assert data["test_id"] == test.id
        assert data["level"] == "L2"
        assert data["total_score"] == 87.5
        assert data["part1_accuracy"] == 88.0
        assert data["part2_confidence"] == 90.0
        assert len(data["part2_items"]) == 2

    @pytest.mark.asyncio
    async def test_get_report_not_found(self, client, auth_teacher):
        """Test getting report for non-existent test."""
        response = await client.get("/api/v1/tests/99999/report")
        assert response.status_code == 404


class TestSubmitPart2:
    """Tests for POST /tests/{test_id}/part2 endpoint."""

    @pytest.mark.asyncio
    async def test_submit_part2_success(self, test_db, student_profile, client, auth_teacher):
        """Test successful Part 2 submission."""
        # Create test in part1_done status
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="part1_done",
            part1_score=Decimal("80.0")
        )
        test_db.add(test)
        
        # Create questions
        question = QuestionModel(
            level="L1",
            unit="Unit 1",
            question_no=1,
            question="What is your name?",
            reference_answer="My name is...",
            is_active=True
        )
        test_db.add(question)
        await test_db.commit()
        await test_db.refresh(test)

        with patch("src.use_cases.evaluate_part2.enqueue_part2_task", new_callable=AsyncMock):
            response = await client.post(
                f"/api/v1/tests/{test.id}/part2",
                json={
                    "audio_url": "https://oss.example.com/audio.mp3"
                }
            )
            assert response.status_code == 200

            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_submit_part2_test_not_found(self, client, auth_teacher):
        """Test Part 2 submission for non-existent test."""
        response = await client.post(
            "/api/v1/tests/99999/part2",
            json={"audio_url": "https://example.com/audio.mp3"}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_part2_no_questions(self, test_db, student_profile, client, auth_teacher):
        """Test Part 2 submission when no questions exist."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L99",  # Non-existent level
            unit="Unit 99",
            status="part1_done"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        response = await client.post(
            f"/api/v1/tests/{test.id}/part2",
            json={"audio_url": "https://example.com/audio.mp3"}
        )
        assert response.status_code == 400
        assert "NoQuestions" in response.json()["detail"]["error"]
