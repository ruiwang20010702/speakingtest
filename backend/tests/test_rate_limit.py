"""
Rate Limiting Middleware Tests

Tests for the rate limiting middleware using Pattern 6 (Async).
"""
import pytest
from unittest.mock import Mock, patch
from httpx import AsyncClient, ASGITransport

from src.infrastructure.rate_limit import RateLimitMiddleware


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    @pytest.mark.asyncio
    async def test_rate_limit_headers_present(self):
        """Test that rate limit headers are present in response for non-excluded endpoints."""
        from src.infrastructure.main import app
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Use an API endpoint (not /health which is excluded)
            response = await client.get("/api/v1/students")
            # Even if unauthorized, headers should be present
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers

    @pytest.mark.asyncio
    async def test_rate_limit_remaining_decreases(self):
        """Test that remaining count decreases with each request."""
        from src.infrastructure.main import app
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Use an API endpoint (not /health which is excluded)
            # First request
            response1 = await client.get("/api/v1/students")
            remaining1 = int(response1.headers.get("X-RateLimit-Remaining", 0))
            
            # Second request
            response2 = await client.get("/api/v1/students")
            remaining2 = int(response2.headers.get("X-RateLimit-Remaining", 0))
            
            # Remaining should decrease
            assert remaining2 < remaining1

    @pytest.mark.asyncio
    async def test_health_check_excluded(self):
        """Test that health check is accessible (not rate limited)."""
        from src.infrastructure.main import app
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_docs_excluded(self):
        """Test that docs endpoints are excluded from rate limiting."""
        from src.infrastructure.main import app
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/docs")
            # Docs page should be accessible
            assert response.status_code in [200, 307]  # May redirect


class TestRateLimitMiddlewareUnit:
    """Unit tests for RateLimitMiddleware internals."""

    def test_get_client_key_with_forwarded_header(self):
        """Test client key extraction with X-Forwarded-For header."""
        middleware = RateLimitMiddleware(app=None, requests_per_minute=60)
        
        mock_request = Mock()
        mock_request.state = Mock()
        mock_request.state.user_id = None
        mock_request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        # Access the private method
        client_key = middleware._get_client_key(mock_request)
        
        assert client_key == "ip:192.168.1.1"

    def test_get_client_key_with_user_id(self):
        """Test client key extraction with authenticated user."""
        middleware = RateLimitMiddleware(app=None, requests_per_minute=60)
        
        mock_request = Mock()
        mock_request.state = Mock()
        mock_request.state.user_id = 123
        
        client_key = middleware._get_client_key(mock_request)
        
        assert client_key == "user:123"

    def test_cleanup_old_requests(self):
        """Test that old requests are cleaned up."""
        import time
        
        middleware = RateLimitMiddleware(app=None, requests_per_minute=60)
        middleware.window_seconds = 60
        
        current_time = time.time()
        middleware.request_counts["test_client"] = [
            current_time - 120,  # Old (should be removed)
            current_time - 30,   # Recent (should stay)
            current_time,        # Now (should stay)
        ]
        
        middleware._cleanup_old_requests("test_client", current_time)
        
        assert len(middleware.request_counts["test_client"]) == 2
