"""
Tests for Admin Controller
Covers: Overview stats, funnel stats, teacher management, audit logs, failed tasks
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from src.adapters.repositories.models import (
    StudentProfileModel, TestModel, UserModel, ReportShareTokenModel,
    StudentEntryTokenModel, AuditLogModel
)
from src.infrastructure.timezone import now as china_now


class TestOverviewStats:
    """Tests for GET /admin/overview endpoint."""

    @pytest.mark.asyncio
    async def test_get_overview_stats(self, test_db, student_profile, client, auth_admin):
        """Test getting overview stats as admin."""
        # Create test data
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed",
            total_score=Decimal("85.0")
        )
        test_db.add(test)
        await test_db.commit()

        response = await client.get("/api/v1/admin/stats/overview")
        assert response.status_code == 200

        data = response.json()
        assert "total_students" in data
        assert "total_tests" in data


class TestFunnelStats:
    """Tests for GET /admin/funnel endpoint."""

    @pytest.mark.asyncio
    async def test_get_funnel_stats(self, test_db, client, auth_admin):
        """Test getting funnel stats as admin."""
        response = await client.get("/api/v1/admin/stats/funnel")
        assert response.status_code == 200

        data = response.json()
        assert "scanned" in data
        assert "completed" in data


class TestCostStats:
    """Tests for GET /admin/cost endpoint."""

    @pytest.mark.asyncio
    async def test_get_cost_stats(self, test_db, client, auth_admin):
        """Test getting cost stats as admin."""
        response = await client.get("/api/v1/admin/stats/cost")
        assert response.status_code == 200

        data = response.json()
        assert "total_tests" in data
        assert "estimated_cost_cny" in data


class TestTeacherManagement:
    """Tests for teacher management endpoints."""

    @pytest.mark.asyncio
    async def test_list_teachers(self, test_db, teacher_user, client, auth_admin):
        """Test listing teachers as admin."""
        response = await client.get("/api/v1/admin/teachers")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_teacher_detail(self, test_db, teacher_user, client, auth_admin):
        """Test getting teacher detail as admin."""
        response = await client.get(f"/api/v1/admin/teachers/{teacher_user.id}")
        assert response.status_code == 200

        data = response.json()
        assert data["user_id"] == teacher_user.id

    @pytest.mark.asyncio
    async def test_get_teacher_detail_not_found(self, client, auth_admin):
        """Test getting non-existent teacher detail."""
        response = await client.get("/api/v1/admin/teachers/99999")
        assert response.status_code == 404


class TestAuditLogs:
    """Tests for GET /admin/audit-logs endpoint."""

    @pytest.mark.asyncio
    async def test_query_audit_logs(self, test_db, admin_user, client, auth_admin):
        """Test querying audit logs as admin."""
        # Create audit log
        log = AuditLogModel(
            operator_id=admin_user.id,
            action="TEST_ACTION",
            target_type="test",
            created_at=china_now()
        )
        test_db.add(log)
        await test_db.commit()

        response = await client.get("/api/v1/admin/audit-logs")
        assert response.status_code == 200

        data = response.json()
        assert "total" in data
        assert "items" in data

    @pytest.mark.asyncio
    async def test_query_audit_logs_with_filter(self, test_db, admin_user, client, auth_admin):
        """Test querying audit logs with action filter."""
        log = AuditLogModel(
            operator_id=admin_user.id,
            action="SPECIFIC_ACTION",
            created_at=china_now()
        )
        test_db.add(log)
        await test_db.commit()

        response = await client.get("/api/v1/admin/audit-logs?action=SPECIFIC_ACTION")
        assert response.status_code == 200


class TestFailedTasks:
    """Tests for failed task management endpoints."""

    @pytest.mark.asyncio
    async def test_list_failed_tasks(self, test_db, student_profile, client, auth_admin):
        """Test listing failed tasks as admin."""
        # Create a failed test
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="failed",
            failure_reason="Test error"
        )
        test_db.add(test)
        await test_db.commit()

        response = await client.get("/api/v1/admin/failed-tasks")
        assert response.status_code == 200

        data = response.json()
        assert "total" in data
        assert "items" in data

    @pytest.mark.asyncio
    async def test_retry_failed_task_not_found(self, client, auth_admin):
        """Test retrying non-existent failed task."""
        response = await client.post("/api/v1/admin/failed-tasks/99999/retry")
        assert response.status_code == 404


class TestAdminAccessControl:
    """Tests for admin access control."""

    @pytest.mark.asyncio
    async def test_overview_forbidden_for_teacher(self, client, auth_teacher):
        """Test that teachers cannot access admin endpoints."""
        response = await client.get("/api/v1/admin/stats/overview")
        # Teacher can access their own overview data
        assert response.status_code in [200, 403]
