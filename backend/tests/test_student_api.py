"""
Student API Tests

Tests for student-related endpoints.
"""
import pytest
from unittest.mock import MagicMock

class TestBatchTokenGeneration:
    """Tests for batch token generation endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("student_ids,expected_total,expected_success,expected_failed", [
        pytest.param([], 0, 0, 0, id="empty_list"),
        pytest.param([99999, 99998], 2, 0, 2, id="nonexistent_students"),
    ])
    async def test_batch_tokens_variations(
        self,
        client,
        test_db,
        teacher_user,
        auth_teacher,
        student_ids,
        expected_total,
        expected_success,
        expected_failed
    ):
        """Test batch token generation with various inputs."""
        response = await client.post(
            "/api/v1/students/batch-tokens",
            json={
                "student_ids": student_ids,
                "level": "L1",
                "unit": "Unit 1"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == expected_total
        assert data["success_count"] == expected_success
        if expected_failed > 0:
            assert data["failed_count"] == expected_failed


class TestTokenRevocation:
    """Tests for token revocation endpoint."""

    @pytest.mark.asyncio
    async def test_revoke_token_not_found(self, client, test_db, teacher_user, auth_teacher):
        """Test token revocation for non-existent student."""
        response = await client.post("/api/v1/students/99999/revoke-token")
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_revoke_token_success(self, client, test_db, teacher_user, student_profile, auth_teacher):
        """Test successful token revocation."""
        response = await client.post(
            f"/api/v1/students/{student_profile.user_id}/revoke-token"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "revoked_count" in data


class TestStudentList:
    """Tests for student list endpoint."""

    @pytest.mark.asyncio
    async def test_list_students_unauthorized(self, client, test_db):
        """Test student list without auth returns 401."""
        response = await client.get("/api/v1/students")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_students_as_teacher(self, client, test_db, teacher_user, student_profile, auth_teacher):
        """Test student list for teacher."""
        response = await client.get("/api/v1/students")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
