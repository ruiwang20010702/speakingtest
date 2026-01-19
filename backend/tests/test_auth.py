"""
Tests for Authentication Module
Covers: password hashing, JWT token creation/decoding, RBAC
"""
import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock

from src.infrastructure.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    TokenData,
    require_role
)


class TestPasswordHashing:
    """Tests for password hashing utilities."""

    def test_hash_password_returns_string(self):
        """Test that hashing returns a string."""
        hashed = hash_password("secret123")
        assert isinstance(hashed, str)
        assert hashed != "secret123"

    def test_hash_password_different_for_same_input(self):
        """Test that same password produces different hashes (due to salt)."""
        hash1 = hash_password("secret123")
        hash2 = hash_password("secret123")
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "mypassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_verify_password_empty(self):
        """Test verifying empty password."""
        hashed = hash_password("nonempty")
        assert verify_password("", hashed) is False


class TestJWTTokens:
    """Tests for JWT token creation and decoding."""

    def test_create_access_token_returns_string(self):
        """Test that token creation returns a string."""
        token = create_access_token({"sub": "123", "role": "teacher"})
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are reasonably long

    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        token = create_access_token({"sub": "42", "role": "admin"})
        result = decode_token(token)
        
        assert result is not None
        assert result.user_id == 42
        assert result.role == "admin"

    def test_decode_token_default_role(self):
        """Test that missing role defaults to 'student'."""
        token = create_access_token({"sub": "100"})
        result = decode_token(token)
        
        assert result is not None
        assert result.role == "student"

    def test_decode_invalid_token(self):
        """Test decoding invalid token returns None."""
        result = decode_token("invalid.token.here")
        assert result is None

    def test_decode_expired_token(self):
        """Test decoding expired token returns None."""
        # Create token that expired 1 hour ago
        token = create_access_token(
            {"sub": "1", "role": "teacher"},
            expires_delta=timedelta(hours=-1)
        )
        result = decode_token(token)
        assert result is None

    def test_decode_token_missing_sub(self):
        """Test decoding token without 'sub' claim returns None."""
        # Create token without 'sub'
        token = create_access_token({"role": "admin"})
        result = decode_token(token)
        assert result is None

    def test_token_with_custom_expiry(self):
        """Test token with custom expiry time."""
        token = create_access_token(
            {"sub": "5", "role": "teacher"},
            expires_delta=timedelta(days=7)
        )
        result = decode_token(token)
        
        assert result is not None
        assert result.user_id == 5


class TestRBAC:
    """Tests for Role-Based Access Control."""

    @pytest.mark.asyncio
    async def test_require_role_allows_matching_role(self):
        """Test that matching role is allowed."""
        checker = require_role("admin", "teacher")
        token = create_access_token({"sub": "1", "role": "admin"})
        
        result = await checker(token)
        assert result == 1

    @pytest.mark.asyncio
    async def test_require_role_denies_non_matching_role(self):
        """Test that non-matching role is denied."""
        from fastapi import HTTPException
        
        checker = require_role("admin")
        token = create_access_token({"sub": "1", "role": "student"})
        
        with pytest.raises(HTTPException) as exc_info:
            await checker(token)
        
        assert exc_info.value.status_code == 403
        assert "not authorized" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_role_denies_invalid_token(self):
        """Test that invalid token is denied."""
        from fastapi import HTTPException
        
        checker = require_role("admin")
        
        with pytest.raises(HTTPException) as exc_info:
            await checker("invalid.token")
        
        assert exc_info.value.status_code == 401


class TestTokenDataModel:
    """Tests for TokenData Pydantic model."""

    def test_token_data_creation(self):
        """Test creating TokenData instance."""
        data = TokenData(user_id=123, role="teacher")
        assert data.user_id == 123
        assert data.role == "teacher"

    def test_token_data_validation(self):
        """Test TokenData validates types."""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            TokenData(user_id="not_an_int", role="teacher")
