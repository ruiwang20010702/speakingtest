"""
Tests for Question Controller
Covers: CRUD operations for question bank
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from src.adapters.repositories.models import QuestionModel


class TestListQuestions:
    """Tests for GET /questions endpoint."""

    @pytest.mark.asyncio
    async def test_list_all_questions(self, test_db, client, auth_admin):
        """Test listing all questions."""
        # Create questions
        q1 = QuestionModel(level="L1", unit="Unit 1", question_no=1, question="Q1")
        q2 = QuestionModel(level="L2", unit="Unit 1", question_no=1, question="Q2")
        test_db.add(q1)
        test_db.add(q2)
        await test_db.commit()

        response = await client.get("/api/v1/questions")
        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.asyncio
    async def test_list_questions_filter_level(self, test_db, client, auth_admin):
        """Test filtering questions by level."""
        q1 = QuestionModel(level="L1", unit="Unit 1", question_no=1, question="Q1")
        q2 = QuestionModel(level="L2", unit="Unit 1", question_no=1, question="Q2")
        test_db.add(q1)
        test_db.add(q2)
        await test_db.commit()

        response = await client.get("/api/v1/questions?level=L1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["level"] == "L1"


class TestGetQuestionsByLevelUnit:
    """Tests for GET /questions/{level}/{unit} endpoint."""

    @pytest.mark.asyncio
    async def test_get_questions_success(self, test_db, client, auth_admin):
        """Test getting questions for specific level/unit."""
        for i in range(3):
            q = QuestionModel(level="L1", unit="Unit 1", question_no=i+1, question=f"Q{i+1}")
            test_db.add(q)
        await test_db.commit()

        response = await client.get("/api/v1/questions/L1/Unit 1")
        assert response.status_code == 200
        assert len(response.json()) == 3

    @pytest.mark.asyncio
    async def test_get_questions_not_found(self, client, auth_admin):
        """Test getting questions for non-existent level/unit."""
        response = await client.get("/api/v1/questions/L99/Unit 99")
        assert response.status_code == 404


class TestCreateQuestion:
    """Tests for POST /questions endpoint."""

    @pytest.mark.asyncio
    async def test_create_question_admin(self, test_db, client, auth_admin):
        """Test creating question as admin."""
        response = await client.post(
            "/api/v1/questions",
            json={
                "level": "L1",
                "unit": "Unit 1",
                "question_no": 1,
                "question": "What is your name?",
                "reference_answer": "My name is..."
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "What is your name?"

    @pytest.mark.asyncio
    async def test_create_question_teacher_forbidden(self, client, auth_teacher):
        """Test creating question as teacher is forbidden."""
        response = await client.post(
            "/api/v1/questions",
            json={
                "level": "L1",
                "unit": "Unit 1",
                "question_no": 1,
                "question": "Test?"
            }
        )
        assert response.status_code == 403


class TestBatchCreateQuestions:
    """Tests for POST /questions/batch endpoint."""

    @pytest.mark.asyncio
    async def test_batch_create_success(self, test_db, client, auth_admin):
        """Test batch creating questions as admin."""
        response = await client.post(
            "/api/v1/questions/batch",
            json={
                "level": "L2",
                "unit": "Unit 2",
                "questions": [
                    {"question_no": 1, "question": "Q1?"},
                    {"question_no": 2, "question": "Q2?"},
                    {"question_no": 3, "question": "Q3?"}
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["created"] == 3


class TestUpdateQuestion:
    """Tests for PUT /questions/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_question_admin(self, test_db, client, auth_admin):
        """Test updating question as admin."""
        q = QuestionModel(level="L1", unit="Unit 1", question_no=1, question="Old Q")
        test_db.add(q)
        await test_db.commit()
        await test_db.refresh(q)

        response = await client.put(
            f"/api/v1/questions/{q.id}",
            json={"question": "New Q"}
        )
        assert response.status_code == 200
        assert response.json()["question"] == "New Q"

    @pytest.mark.asyncio
    async def test_update_question_not_found(self, client, auth_admin):
        """Test updating non-existent question."""
        response = await client.put(
            "/api/v1/questions/99999",
            json={"question": "New Q"}
        )
        assert response.status_code == 404


class TestDeleteQuestion:
    """Tests for DELETE /questions/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_question_admin(self, test_db, client, auth_admin):
        """Test deleting question as admin."""
        q = QuestionModel(level="L1", unit="Unit 1", question_no=1, question="Q")
        test_db.add(q)
        await test_db.commit()
        await test_db.refresh(q)

        response = await client.delete(f"/api/v1/questions/{q.id}")
        assert response.status_code == 200

        # Verify soft delete
        await test_db.refresh(q)
        assert q.is_active is False

    @pytest.mark.asyncio
    async def test_delete_question_not_found(self, client, auth_admin):
        """Test deleting non-existent question."""
        response = await client.delete("/api/v1/questions/99999")
        assert response.status_code == 404
