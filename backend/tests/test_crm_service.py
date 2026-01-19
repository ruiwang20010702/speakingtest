"""
Tests for CRM Service
Covers: fetch_crm_user_info, update_user_crm_info
"""
import pytest
import respx
import httpx
from unittest.mock import MagicMock, AsyncMock

from src.infrastructure.crm_service import (
    fetch_crm_user_info,
    update_user_crm_info,
    CRMUserInfo,
    CRM_API_BASE_URL
)


class TestFetchCRMUserInfo:
    """Tests for fetch_crm_user_info function."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_success(self):
        """Test successful CRM user info fetch."""
        mock_response = {
            "code": 200,
            "message": "success",
            "data": {
                "ss_name": "张三",
                "ss_sm_name": "主管",
                "ss_dept4_name": "SS部门",
                "ss_group": "A组",
                "ss_crm_name": "zhangsan",
                "ss_email_addr": "zhangsan@51talk.com"
            }
        }

        respx.get(url__regex=r".*/domestic-ss/upgrade-28.*").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await fetch_crm_user_info("zhangsan@51talk.com")

        assert result is not None
        assert result.ss_name == "张三"
        assert result.ss_crm_name == "zhangsan"
        assert result.ss_email_addr == "zhangsan@51talk.com"

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_user_not_found(self):
        """Test CRM user not found."""
        mock_response = {
            "code": 200,
            "message": "success",
            "data": {}
        }

        respx.get(url__regex=r".*/domestic-ss/upgrade-28.*").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await fetch_crm_user_info("unknown@51talk.com")
        assert result is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_api_error(self):
        """Test CRM API returns error code."""
        mock_response = {
            "code": 500,
            "message": "Internal Server Error"
        }

        respx.get(url__regex=r".*/domestic-ss/upgrade-28.*").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await fetch_crm_user_info("test@51talk.com")
        assert result is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_http_error(self):
        """Test CRM API HTTP error."""
        respx.get(url__regex=r".*/domestic-ss/upgrade-28.*").mock(
            return_value=httpx.Response(500)
        )

        result = await fetch_crm_user_info("test@51talk.com")
        assert result is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_timeout(self):
        """Test CRM API timeout."""
        respx.get(url__regex=r".*/domestic-ss/upgrade-28.*").mock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        result = await fetch_crm_user_info("test@51talk.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_empty_email(self):
        """Test with empty email."""
        result = await fetch_crm_user_info("")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_none_email(self):
        """Test with None email."""
        result = await fetch_crm_user_info(None)
        assert result is None


class TestUpdateUserCRMInfo:
    """Tests for update_user_crm_info function."""

    @pytest.mark.asyncio
    async def test_update_success(self, test_db, teacher_user):
        """Test successful CRM info update."""
        crm_info = CRMUserInfo(
            ss_name="张三",
            ss_sm_name="主管",
            ss_dept4_name="SS部门",
            ss_group="A组",
            ss_crm_name="zhangsan",
            ss_email_addr="zhangsan@51talk.com"
        )

        result = await update_user_crm_info(test_db, teacher_user, crm_info)

        assert result is True
        assert teacher_user.ss_name == "张三"
        assert teacher_user.ss_crm_name == "zhangsan"
        assert teacher_user.crm_synced_at is not None

    @pytest.mark.asyncio
    async def test_update_partial_info(self, test_db, teacher_user):
        """Test update with partial CRM info."""
        crm_info = CRMUserInfo(
            ss_crm_name="only_crm_name"
        )

        result = await update_user_crm_info(test_db, teacher_user, crm_info)

        assert result is True
        assert teacher_user.ss_crm_name == "only_crm_name"
        # Other fields should remain unchanged (None or original)

    @pytest.mark.asyncio
    async def test_update_none_info(self, test_db, teacher_user):
        """Test update with None CRM info."""
        result = await update_user_crm_info(test_db, teacher_user, None)
        assert result is False


class TestCRMUserInfoDataclass:
    """Tests for CRMUserInfo dataclass."""

    def test_create_full(self):
        """Test creating with all fields."""
        info = CRMUserInfo(
            ss_name="Name",
            ss_sm_name="SM",
            ss_dept4_name="Dept",
            ss_group="Group",
            ss_crm_name="CRM",
            ss_email_addr="email@test.com"
        )
        assert info.ss_name == "Name"
        assert info.ss_email_addr == "email@test.com"

    def test_create_partial(self):
        """Test creating with partial fields."""
        info = CRMUserInfo(ss_crm_name="crm_only")
        assert info.ss_crm_name == "crm_only"
        assert info.ss_name is None
        assert info.ss_email_addr is None

    def test_create_empty(self):
        """Test creating empty dataclass."""
        info = CRMUserInfo()
        assert info.ss_name is None
        assert info.ss_crm_name is None
