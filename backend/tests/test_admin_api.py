"""
Admin API Tests

Tests for admin-related endpoints.
"""
import pytest
from src.adapters.repositories.models import TestModel, AuditLogModel


class TestAdminStats:
    """Tests for admin statistics endpoints."""

    @pytest.mark.asyncio
    async def test_overview_stats(self, client, test_db, admin_user, auth_admin):
        """Test overview stats endpoint."""
        response = await client.get("/api/v1/admin/stats/overview")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_students" in data
        assert "total_tests" in data

    @pytest.mark.asyncio
    async def test_funnel_stats(self, client, test_db, admin_user, auth_admin):
        """Test funnel stats endpoint."""
        response = await client.get("/api/v1/admin/stats/funnel")
        
        assert response.status_code == 200
        data = response.json()
        assert "scanned" in data
        assert "completed" in data

    @pytest.mark.asyncio
    async def test_cost_stats(self, client, test_db, admin_user, auth_admin):
        """Test cost stats endpoint."""
        response = await client.get("/api/v1/admin/stats/cost")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_tests" in data
        assert "estimated_cost_cny" in data


class TestTeacherManagement:
    """Tests for teacher management endpoints."""

    @pytest.mark.asyncio
    async def test_list_teachers(self, client, test_db, admin_user, teacher_user, auth_admin):
        """Test listing all teachers."""
        response = await client.get("/api/v1/admin/teachers")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_teacher_not_found(self, client, test_db, admin_user, auth_admin):
        """Test getting non-existent teacher."""
        response = await client.get("/api/v1/admin/teachers/99999")
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_teacher_detail(self, client, test_db, admin_user, teacher_user, student_profile, auth_admin):
        """Test getting teacher detail."""
        response = await client.get(f"/api/v1/admin/teachers/{teacher_user.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == teacher_user.id
        assert "student_count" in data


class TestAuditLogs:
    """Tests for audit log query endpoint."""

    @pytest.mark.asyncio
    async def test_query_audit_logs_empty(self, client, test_db, admin_user, auth_admin):
        """Test querying audit logs when empty."""
        response = await client.get("/api/v1/admin/audit-logs")
        
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_query_audit_logs_with_data(self, client, test_db, admin_user, teacher_user, auth_admin):
        """Test querying audit logs with data."""
        # Create audit log
        log = AuditLogModel(
            operator_id=teacher_user.id,
            action="TEST_ACTION",
            target_type="test",
            target_id=1,
            details={"test": "data"},
            client_ip="127.0.0.1"
        )
        test_db.add(log)
        await test_db.commit()
        
        response = await client.get("/api/v1/admin/audit-logs")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_query_audit_logs_filter_by_action(self, client, test_db, admin_user, teacher_user, auth_admin):
        """Test filtering audit logs by action."""
        # Create audit log
        log = AuditLogModel(
            operator_id=teacher_user.id,
            action="SPECIFIC_ACTION",
            target_type="test",
            target_id=1
        )
        test_db.add(log)
        await test_db.commit()
        
        response = await client.get("/api/v1/admin/audit-logs?action=SPECIFIC_ACTION")
        
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["action"] == "SPECIFIC_ACTION"


class TestFailedTaskManagement:
    """Tests for failed task management endpoints."""

    @pytest.mark.asyncio
    async def test_list_failed_tasks_empty(self, client, test_db, admin_user, auth_admin):
        """Test listing failed tasks when empty."""
        response = await client.get("/api/v1/admin/failed-tasks")
        
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data

    @pytest.mark.asyncio
    async def test_list_failed_tasks_with_data(self, client, test_db, admin_user, student_profile, auth_admin):
        """Test listing failed tasks with data."""
        # Create failed test
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="failed",
            failure_reason="Test error",
            retry_count=1
        )
        test_db.add(test)
        await test_db.commit()
        
        response = await client.get("/api/v1/admin/failed-tasks")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_retry_failed_task_not_found(self, client, test_db, admin_user, auth_admin):
        """Test retrying non-existent task."""
        response = await client.post("/api/v1/admin/failed-tasks/99999/retry")
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_retry_non_failed_task(self, client, test_db, admin_user, student_profile, auth_admin):
        """Test retrying a completed (non-failed) task."""
        # Create completed test
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1",
            unit="Unit 1",
            status="completed"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)
        
        response = await client.post(f"/api/v1/admin/failed-tasks/{test.id}/retry")
        
        # Should fail - can only retry failed tests
        assert response.status_code == 400
