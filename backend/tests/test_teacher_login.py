"""
Tests for Teacher Login Use Cases
Covers: SendVerificationCodeUseCase, TeacherLoginUseCase
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import timedelta

from src.use_cases.teacher_login import (
    SendVerificationCodeUseCase, SendCodeRequest, SendCodeResponse,
    TeacherLoginUseCase, LoginRequest, LoginResponse
)
from src.adapters.repositories.models import UserModel, VerificationCodeModel
from src.infrastructure.timezone import now as china_now


class TestSendVerificationCodeUseCase:
    """Tests for sending verification codes."""

    @pytest.mark.asyncio
    async def test_send_code_success(self, test_db):
        """Test successful code sending."""
        request = SendCodeRequest(
            email="teacher@51talk.com",
            ip_address="127.0.0.1"
        )

        with patch.object(SendVerificationCodeUseCase, '_generate_code', return_value="123456"):
            with patch("src.use_cases.teacher_login.get_email_service") as mock_service:
                mock_email = MagicMock()
                mock_email.send_verification_code = AsyncMock(return_value=True)
                mock_service.return_value = mock_email

                use_case = SendVerificationCodeUseCase(test_db)
                response = await use_case.execute(request)

                assert response.success is True
                assert "已发送" in response.message

    @pytest.mark.asyncio
    async def test_send_code_invalid_email(self, test_db):
        """Test sending to non-51talk email fails."""
        request = SendCodeRequest(email="user@gmail.com")

        use_case = SendVerificationCodeUseCase(test_db)
        response = await use_case.execute(request)

        assert response.success is False
        assert "51talk.com" in response.message

    @pytest.mark.asyncio
    async def test_send_code_admin_bypass(self, test_db):
        """Test admin email bypasses verification."""
        request = SendCodeRequest(email="704778107@qq.com")

        use_case = SendVerificationCodeUseCase(test_db)
        response = await use_case.execute(request)

        assert response.success is True
        assert "无需验证码" in response.message

    @pytest.mark.asyncio
    async def test_send_code_rate_limit(self, test_db):
        """Test rate limiting prevents frequent sends."""
        # First, create a recent code
        recent_code = VerificationCodeModel(
            email="teacher@51talk.com",
            code="111111",
            purpose="login",
            expires_at=china_now() + timedelta(minutes=5),
            created_at=china_now()
        )
        test_db.add(recent_code)
        await test_db.commit()

        request = SendCodeRequest(email="teacher@51talk.com")

        use_case = SendVerificationCodeUseCase(test_db)
        response = await use_case.execute(request)

        assert response.success is False
        assert "频繁" in response.message

    @pytest.mark.asyncio
    async def test_send_code_email_failure(self, test_db):
        """Test handling of email sending failure."""
        request = SendCodeRequest(email="teacher@51talk.com")

        with patch("src.use_cases.teacher_login.get_email_service") as mock_service:
            mock_email = MagicMock()
            mock_email.send_verification_code = AsyncMock(return_value=False)
            mock_service.return_value = mock_email

            use_case = SendVerificationCodeUseCase(test_db)
            response = await use_case.execute(request)

            assert response.success is False
            assert "邮件发送失败" in response.message


class TestTeacherLoginUseCase:
    """Tests for teacher login."""

    @pytest.mark.asyncio
    async def test_login_success(self, test_db):
        """Test successful login."""
        # Create verification code
        valid_code = VerificationCodeModel(
            email="teacher@51talk.com",
            code="123456",
            purpose="login",
            expires_at=china_now() + timedelta(minutes=5),
            is_used=False
        )
        test_db.add(valid_code)
        await test_db.commit()

        request = LoginRequest(
            email="teacher@51talk.com",
            code="123456"
        )

        with patch("src.use_cases.teacher_login.fetch_crm_user_info", new_callable=AsyncMock) as mock_crm:
            mock_crm.return_value = None

            use_case = TeacherLoginUseCase(test_db)
            response = await use_case.execute(request)

            assert response.success is True
            assert response.access_token is not None
            assert response.role == "teacher"

    @pytest.mark.asyncio
    async def test_login_admin_bypass(self, test_db):
        """Test admin can login with any code."""
        request = LoginRequest(
            email="704778107@qq.com",
            code="999999"
        )

        with patch("src.use_cases.teacher_login.fetch_crm_user_info", new_callable=AsyncMock) as mock_crm:
            mock_crm.return_value = None

            use_case = TeacherLoginUseCase(test_db)
            response = await use_case.execute(request)

            assert response.success is True
            assert response.role == "admin"

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, test_db):
        """Test login with invalid email fails."""
        request = LoginRequest(
            email="user@gmail.com",
            code="123456"
        )

        use_case = TeacherLoginUseCase(test_db)
        response = await use_case.execute(request)

        assert response.success is False
        assert response.error == "InvalidEmail"

    @pytest.mark.asyncio
    async def test_login_wrong_code(self, test_db):
        """Test login with wrong code fails."""
        request = LoginRequest(
            email="teacher@51talk.com",
            code="wrong1"
        )

        use_case = TeacherLoginUseCase(test_db)
        response = await use_case.execute(request)

        assert response.success is False
        assert response.error == "CodeInvalid"

    @pytest.mark.asyncio
    async def test_login_expired_code(self, test_db):
        """Test login with expired code fails."""
        # Create expired code
        expired_code = VerificationCodeModel(
            email="teacher@51talk.com",
            code="123456",
            purpose="login",
            expires_at=china_now() - timedelta(minutes=10),  # Expired
            is_used=False
        )
        test_db.add(expired_code)
        await test_db.commit()

        request = LoginRequest(
            email="teacher@51talk.com",
            code="123456"
        )

        use_case = TeacherLoginUseCase(test_db)
        response = await use_case.execute(request)

        assert response.success is False
        assert response.error == "CodeExpired"

    @pytest.mark.asyncio
    async def test_login_used_code(self, test_db):
        """Test login with already used code fails."""
        # Create used code
        used_code = VerificationCodeModel(
            email="teacher@51talk.com",
            code="123456",
            purpose="login",
            expires_at=china_now() + timedelta(minutes=5),
            is_used=True,
            used_at=china_now()
        )
        test_db.add(used_code)
        await test_db.commit()

        request = LoginRequest(
            email="teacher@51talk.com",
            code="123456"
        )

        use_case = TeacherLoginUseCase(test_db)
        response = await use_case.execute(request)

        assert response.success is False
        assert response.error == "CodeUsed"

    @pytest.mark.asyncio
    async def test_login_creates_new_user(self, test_db):
        """Test login creates new user if not exists."""
        # Create valid code
        valid_code = VerificationCodeModel(
            email="newteacher@51talk.com",
            code="123456",
            purpose="login",
            expires_at=china_now() + timedelta(minutes=5),
            is_used=False
        )
        test_db.add(valid_code)
        await test_db.commit()

        request = LoginRequest(
            email="newteacher@51talk.com",
            code="123456"
        )

        with patch("src.use_cases.teacher_login.fetch_crm_user_info", new_callable=AsyncMock) as mock_crm:
            mock_crm.return_value = None

            use_case = TeacherLoginUseCase(test_db)
            response = await use_case.execute(request)

            assert response.success is True
            assert response.user_id is not None

    @pytest.mark.asyncio
    async def test_login_existing_user(self, test_db):
        """Test login with existing user."""
        # Create existing user
        existing_user = UserModel(
            email="existing@51talk.com",
            role="teacher",
            status=1
        )
        test_db.add(existing_user)
        
        # Create valid code
        valid_code = VerificationCodeModel(
            email="existing@51talk.com",
            code="123456",
            purpose="login",
            expires_at=china_now() + timedelta(minutes=5),
            is_used=False
        )
        test_db.add(valid_code)
        await test_db.commit()

        request = LoginRequest(
            email="existing@51talk.com",
            code="123456"
        )

        with patch("src.use_cases.teacher_login.fetch_crm_user_info", new_callable=AsyncMock) as mock_crm:
            mock_crm.return_value = None

            use_case = TeacherLoginUseCase(test_db)
            response = await use_case.execute(request)

            assert response.success is True
            assert response.user_id == existing_user.id
