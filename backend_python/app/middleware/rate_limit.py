"""Rate limiting middleware."""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable
from app.db.connection import get_pool
from datetime import datetime, timedelta
import asyncio


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce per-user token quotas."""
    
    DEFAULT_MONTHLY_QUOTA = 100000  # Default: 100k tokens per month
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limits before processing request."""
        # Skip rate limiting for health checks and admin endpoints
        if request.url.path in ["/health", "/api/health"] or request.url.path.startswith("/api/v1/admin"):
            return await call_next(request)
        
        # Extract user ID from request (default to "anonymous" if not present)
        # TODO: Extract from auth token/JWT
        user_id = request.headers.get("X-User-ID", "anonymous")
        
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                # Get or create user quota record
                user_row = await conn.fetchrow(
                    """
                    SELECT monthly_quota_tokens, tokens_used, quota_reset_date
                    FROM users
                    WHERE id = $1
                    """,
                    user_id,
                )
                
                if not user_row:
                    # Create default user record
                    reset_date = (datetime.now() + timedelta(days=30)).isoformat()
                    await conn.execute(
                        """
                        INSERT INTO users (id, monthly_quota_tokens, tokens_used, quota_reset_date)
                        VALUES ($1, $2, 0, $3)
                        """,
                        user_id,
                        self.DEFAULT_MONTHLY_QUOTA,
                        reset_date,
                    )
                    quota = self.DEFAULT_MONTHLY_QUOTA
                    tokens_used = 0
                else:
                    quota = user_row["monthly_quota_tokens"]
                    tokens_used = user_row["tokens_used"]
                    
                    # Reset quota if reset date passed
                    reset_date = user_row.get("quota_reset_date")
                    if reset_date and datetime.fromisoformat(reset_date) < datetime.now():
                        await conn.execute(
                            """
                            UPDATE users
                            SET tokens_used = 0,
                                quota_reset_date = $1
                            WHERE id = $2
                            """,
                            (datetime.now() + timedelta(days=30)).isoformat(),
                            user_id,
                        )
                        tokens_used = 0
                
                # Check if quota exceeded
                if tokens_used >= quota:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Monthly token quota exceeded ({tokens_used}/{quota})",
                    )
                
                # Process request
                response = await call_next(request)
                
                # TODO: Estimate tokens from request/response and update tokens_used
                # For now, we'll just pass through
                
                return response
                
        except HTTPException:
            raise
        except Exception as e:
            # On error, allow request through (fail open)
            print(f"Rate limit check error: {e}")
            return await call_next(request)

