"""
Report API Tests

Tests for report-related endpoints.
"""
import pytest
from src.adapters.repositories.models import TestModel, ReportShareTokenModel


class TestShareLinkRevocation:
    """Tests for share link revocation endpoint."""

    @pytest.mark.asyncio
    async def test_revoke_share_not_found(self, client, test_db, teacher_user, auth_teacher):
        """Test revoke share for non-existent test."""
        response = await client.post("/api/v1/tests/99999/revoke-share")
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_revoke_share_success(self, client, test_db, teacher_user, student_profile, auth_teacher):
        """Test successful share link revocation."""
        # Create test
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)
        
        # Create share token
        share = ReportShareTokenModel(
            token="test-share-token-123",
            test_id=test.id,
            created_by=teacher_user.id,
            is_revoked=False
        )
        test_db.add(share)
        await test_db.commit()
        
        response = await client.post(f"/api/v1/tests/{test.id}/revoke-share")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["revoked_count"] >= 1


class TestParentView:
    """Tests for parent report viewing endpoint."""

    @pytest.mark.asyncio
    async def test_view_report_invalid_token(self, client, test_db):
        """Test viewing report with invalid token."""
        response = await client.get("/api/v1/reports/invalid-token-xyz")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_view_report_valid_token(self, client, test_db, teacher_user, student_profile):
        """Test viewing report with valid token."""
        # Create test
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed",
            part1_score=85.0,
            part2_score=90.0,
            total_score=87.5,
            star_level=4
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)
        
        # Create share token
        share = ReportShareTokenModel(
            token="valid-share-token-abc",
            test_id=test.id,
            created_by=teacher_user.id,
            is_revoked=False
        )
        test_db.add(share)
        await test_db.commit()
        
        response = await client.get("/api/v1/reports/valid-share-token-abc")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "total_score" in data

    @pytest.mark.asyncio
    async def test_view_report_revoked_token(self, client, test_db, teacher_user, student_profile):
        """Test viewing report with revoked token."""
        # Create test
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)
        
        # Create revoked share token
        share = ReportShareTokenModel(
            token="revoked-token-xyz",
            test_id=test.id,
            created_by=teacher_user.id,
            is_revoked=True
        )
        test_db.add(share)
        await test_db.commit()
        
        response = await client.get("/api/v1/reports/revoked-token-xyz")
        
        # Should fail - token is revoked
        assert response.status_code in [403, 404]
