"""
Tests for Report Controller - Complete Endpoint Coverage
Covers: Student tests, report detail, share links, parent H5, interpretation
"""
import pytest
from decimal import Decimal
from datetime import timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from src.adapters.repositories.models import (
    TestModel, TestItemModel, StudentProfileModel, ReportShareTokenModel
)
from src.infrastructure.timezone import now as china_now


# ============================================
# Student Test History
# ============================================

class TestGetStudentTests:
    """Tests for GET /students/{student_id}/tests endpoint."""

    @pytest.mark.asyncio
    async def test_get_student_tests_as_teacher(self, test_db, student_profile, client, auth_teacher):
        """Test getting student tests as teacher."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed",
            total_score=Decimal("85.0")
        )
        test_db.add(test)
        await test_db.commit()

        response = await client.get(f"/api/v1/students/{student_profile.user_id}/tests")
        assert response.status_code == 200
        assert len(response.json()) >= 1

    @pytest.mark.asyncio
    async def test_get_student_tests_as_admin(self, test_db, student_profile, client, auth_admin):
        """Test getting student tests as admin."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L2",
            unit="Unit 2",
            status="pending"
        )
        test_db.add(test)
        await test_db.commit()

        response = await client.get(f"/api/v1/students/{student_profile.user_id}/tests")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_student_tests_unauthorized(self, client, auth_teacher):
        """Test accessing non-owned student is forbidden."""
        response = await client.get("/api/v1/students/99999/tests")
        assert response.status_code == 403


# ============================================
# Test Report Detail
# ============================================

class TestGetTestReport:
    """Tests for GET /tests/{test_id} endpoint (report detail)."""

    @pytest.mark.asyncio
    async def test_get_report_detail_completed(self, test_db, student_profile, client, auth_teacher):
        """Test getting completed report detail."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed",
            part1_score=Decimal("80.0"),
            part2_score=Decimal("90.0"),
            total_score=Decimal("85.0"),
            star_level=4
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        response = await client.get(f"/api/v1/tests/{test.id}")
        assert response.status_code == 200


# ============================================
# Share Link Generation
# ============================================

class TestGenerateShareLink:
    """Tests for POST /tests/{test_id}/share endpoint."""

    @pytest.mark.asyncio
    async def test_generate_share_link_success(self, test_db, student_profile, client, auth_teacher):
        """Test generating share link."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed",
            total_score=Decimal("85.0")
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        response = await client.post(f"/api/v1/tests/{test.id}/share")
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "share_url" in data

    @pytest.mark.asyncio
    async def test_generate_share_link_idempotent(self, test_db, student_profile, client, auth_teacher):
        """Test share link generation is idempotent."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        # First call
        r1 = await client.post(f"/api/v1/tests/{test.id}/share")
        # Second call
        r2 = await client.post(f"/api/v1/tests/{test.id}/share")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["token"] == r2.json()["token"]

    @pytest.mark.asyncio
    async def test_generate_share_link_not_found(self, client, auth_teacher):
        """Test generating share link for non-existent test."""
        response = await client.post("/api/v1/tests/99999/share")
        assert response.status_code == 404


# ============================================
# Share Link Revocation
# ============================================

class TestRevokeShareLink:
    """Tests for DELETE /tests/{test_id}/share endpoint."""

    @pytest.mark.asyncio
    async def test_revoke_share_link_success(self, test_db, student_profile, client, auth_teacher):
        """Test revoking share link."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        # Create share token first
        await client.post(f"/api/v1/tests/{test.id}/share")

        # Revoke (POST /revoke-share)
        response = await client.post(f"/api/v1/tests/{test.id}/revoke-share")
        assert response.status_code == 200
        assert response.json()["success"] is True


# ============================================
# Report Override (Editing)
# ============================================

class TestReportOverride:
    """Tests for report override endpoints."""

    @pytest.mark.asyncio
    async def test_get_report_override(self, test_db, student_profile, client, auth_teacher):
        """Test getting report override data."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed",
            total_score=Decimal("85.0")
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        # Correct path: /tests/{test_id}/report/override
        response = await client.get(f"/api/v1/tests/{test.id}/report/override")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_report_override(self, test_db, student_profile, client, auth_teacher):
        """Test updating report with override."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        # Correct path: /tests/{test_id}/report (PATCH)
        response = await client.patch(
            f"/api/v1/tests/{test.id}/report",
            json={
                "student_name": "Override Name",
                "star_level": 5
            }
        )
        if response.status_code != 200:
            print(f"Update failed: {response.status_code} {response.text}")
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_reset_report_override(self, test_db, student_profile, client, auth_teacher):
        """Test resetting report override."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        # Correct path: /tests/{test_id}/report/override
        response = await client.delete(f"/api/v1/tests/{test.id}/report/override")
        assert response.status_code == 200


# ============================================
# Parent View (Public)
# ============================================

class TestParentView:
    """Tests for public parent view endpoints."""

    @pytest.mark.asyncio
    async def test_view_report_by_token(self, test_db, student_profile, client):
        """Test viewing report via share token."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed",
            total_score=Decimal("85.0")
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        token = ReportShareTokenModel(
            test_id=test.id,
            token="valid-share-token-123",
            expires_at=china_now() + timedelta(days=30),
            is_revoked=False,
            created_by=1
        )
        test_db.add(token)
        await test_db.commit()

        # Correct path: /reports/{token}
        response = await client.get("/api/v1/reports/valid-share-token-123")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_view_report_invalid_token(self, client):
        """Test viewing report with invalid token."""
        # Correct path: /reports/{token}
        response = await client.get("/api/v1/reports/invalid-token-xyz")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_parent_h5_report(self, test_db, student_profile, client):
        """Test getting parent H5 report data."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed",
            total_score=Decimal("85.0"),
            star_level=4,
            part1_score=Decimal("80.0"),
            part2_score=Decimal("90.0"),
            part1_raw_result={"words": []},
            part2_raw_result={"fluency_score": 85}
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        token = ReportShareTokenModel(
            test_id=test.id,
            token="h5-report-token",
            expires_at=china_now() + timedelta(days=30),
            is_revoked=False,
            created_by=1
        )
        test_db.add(token)
        await test_db.commit()

        # Correct path: /reports/{token}/h5
        response = await client.get("/api/v1/reports/h5-report-token/h5")
        assert response.status_code == 200


# ============================================
# Report Interpretation
# ============================================

class TestReportInterpretation:
    """Tests for report interpretation endpoints."""

    @pytest.mark.asyncio
    async def test_get_interpretation_not_generated(self, test_db, student_profile, client, auth_teacher):
        """Test getting interpretation when not yet generated."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        response = await client.get(f"/api/v1/tests/{test.id}/interpretation")
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_get_interpretation_status(self, test_db, student_profile, client, auth_teacher):
        """Test getting interpretation generation status."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        response = await client.get(f"/api/v1/tests/{test.id}/interpretation/status")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_generate_interpretation(self, test_db, student_profile, client, auth_teacher):
        """Test generating report interpretation."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed",
            total_score=Decimal("85.0")
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        response = await client.post(f"/api/v1/tests/{test.id}/interpretation")
        assert response.status_code in [200, 202]
