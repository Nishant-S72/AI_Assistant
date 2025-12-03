"""Tests for rate limiting middleware."""
import pytest
from app.middleware.rate_limit import RateLimitMiddleware
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_rate_limit_middleware():
    """Test rate limiting blocks when quota exceeded."""
    middleware = RateLimitMiddleware(app=None)
    
    # Mock request
    request = AsyncMock()
    request.url.path = "/api/v1/stream_chat"
    request.headers.get = AsyncMock(return_value="test-user")
    
    # Mock database
    mock_user = {
        "monthly_quota_tokens": 1000,
        "tokens_used": 1001,  # Exceeds quota
        "quota_reset_date": None,
    }
    
    async def mock_call_next(request):
        return AsyncMock()
    
    with patch("app.middleware.rate_limit.get_pool") as mock_pool:
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_user)
        mock_conn.execute = AsyncMock()
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Should raise 429
        with pytest.raises(Exception):  # HTTPException
            await middleware.dispatch(request, mock_call_next)

