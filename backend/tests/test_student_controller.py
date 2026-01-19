"""
Tests for Student Controller
Covers: Entry token verification, student list, token generation
"""
import pytest
from decimal import Decimal
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from src.adapters.repositories.models import (
    StudentProfileModel, UserModel, StudentEntryTokenModel, TestModel
)
from src.infrastructure.timezone import now as china_now


class TestStudentEntry:
    """Tests for POST /students/entry endpoint."""

    @pytest.mark.asyncio
    async def test_entry_valid_token(self, test_db, student_profile, client, teacher_user):
        """Test successful entry with valid token."""
        # Create entry token
        token = StudentEntryTokenModel(
            student_id=student_profile.user_id,
            token="valid-entry-token",
            level="L1",
            unit="Unit 1",
            created_by=teacher_user.id,
            expires_at=china_now() + timedelta(hours=24)
        )
        test_db.add(token)
        await test_db.commit()

        response = await client.post(
            "/api/v1/students/entry",
            json={"token": "valid-entry-token"}
        )
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert data["student_name"] == student_profile.student_name

    @pytest.mark.asyncio
    async def test_entry_invalid_token(self, client):
        """Test entry with invalid token."""
        response = await client.post(
            "/api/v1/students/entry",
            json={"token": "non-existent-token"}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_entry_expired_token(self, test_db, student_profile, client, teacher_user):
        """Test entry with expired token."""
        token = StudentEntryTokenModel(
            student_id=student_profile.user_id,
            token="expired-entry-token",
            level="L1",
            unit="Unit 1",
            created_by=teacher_user.id,
            expires_at=china_now() - timedelta(hours=1)  # Expired
        )
        test_db.add(token)
        await test_db.commit()

        response = await client.post(
            "/api/v1/students/entry",
            json={"token": "expired-entry-token"}
        )
        assert response.status_code == 400


class TestListStudents:
    """Tests for GET /students endpoint."""

    @pytest.mark.asyncio
    async def test_list_students_as_teacher(self, test_db, student_profile, client, auth_teacher):
        """Test listing students as teacher."""
        response = await client.get("/api/v1/students")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["student_name"] == student_profile.student_name

    @pytest.mark.asyncio
    async def test_list_students_as_admin(self, test_db, student_profile, client, auth_admin):
        """Test listing students as admin."""
        response = await client.get("/api/v1/students")
        assert response.status_code == 200


class TestGenerateStudentToken:
    """Tests for POST /students/{id}/token endpoint."""

    @pytest.mark.asyncio
    async def test_generate_token_success(self, test_db, student_profile, client, auth_teacher):
        """Test generating token for student."""
        response = await client.post(
            f"/api/v1/students/{student_profile.user_id}/token?level=L1&unit=Unit 1"
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert "entry_url" in data

    @pytest.mark.asyncio
    async def test_generate_token_student_not_found(self, client, auth_teacher):
        """Test generating token for non-existent student."""
        response = await client.post("/api/v1/students/99999/token")
        assert response.status_code == 404


class TestBatchGenerateTokens:
    """Tests for POST /students/batch-tokens endpoint."""

    @pytest.mark.asyncio
    async def test_batch_generate_success(self, test_db, student_profile, client, auth_teacher):
        """Test batch token generation."""
        response = await client.post(
            "/api/v1/students/batch-tokens",
            json={
                "student_ids": [student_profile.user_id],
                "level": "L2",
                "unit": "Unit 2"
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["success_count"] == 1

    @pytest.mark.asyncio
    async def test_batch_generate_partial_success(self, test_db, student_profile, client, auth_teacher):
        """Test batch with some invalid students."""
        response = await client.post(
            "/api/v1/students/batch-tokens",
            json={
                "student_ids": [student_profile.user_id, 99999],
                "level": "L1",
                "unit": "Unit 1"
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 2
        assert data["success_count"] == 1
        assert data["failed_count"] == 1


class TestRevokeToken:
    """Tests for POST /students/{id}/revoke-token endpoint."""

    @pytest.mark.asyncio
    async def test_revoke_token_success(self, test_db, student_profile, teacher_user, client, auth_teacher):
        """Test revoking student tokens."""
        # Create unused token
        token = StudentEntryTokenModel(
            student_id=student_profile.user_id,
            token="to-be-revoked",
            level="L1",
            unit="Unit 1",
            created_by=teacher_user.id,
            expires_at=china_now() + timedelta(hours=24),
            is_used=False
        )
        test_db.add(token)
        await test_db.commit()

        response = await client.post(f"/api/v1/students/{student_profile.user_id}/revoke-token")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["revoked_count"] >= 1

    @pytest.mark.asyncio
    async def test_revoke_token_student_not_found(self, client, auth_teacher):
        """Test revoking token for non-existent student."""
        response = await client.post("/api/v1/students/99999/revoke-token")
        assert response.status_code == 404
