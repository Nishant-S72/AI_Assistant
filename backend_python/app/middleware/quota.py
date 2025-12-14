"""Rate limiting and quota middleware."""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional
from app.db.connection import get_pool
from datetime import datetime, timedelta
import json


async def check_user_quota(user_id: str) -> tuple[bool, Optional[dict]]:
    """
    Check if user has exceeded monthly quota.
    
    Returns:
        (allowed, quota_info) - allowed is False if quota exceeded
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Get or create user quota
            quota_row = await conn.fetchrow(
                """
                SELECT monthly_quota_tokens, tokens_used, last_reset_at
                FROM user_quotas
                WHERE user_id = $1
                """,
                user_id,
            )
            
            if not quota_row:
                # Create default quota (100k tokens/month)
                default_quota = 100000
                await conn.execute(
                    """
                    INSERT INTO user_quotas (user_id, monthly_quota_tokens, tokens_used, last_reset_at)
                    VALUES ($1, $2, 0, $3)
                    """,
                    user_id,
                    default_quota,
                    datetime.now(),
                )
                return (True, {
                    "quota": default_quota,
                    "used": 0,
                    "remaining": default_quota,
                })
            
            quota = quota_row["monthly_quota_tokens"]
            used = quota_row["tokens_used"]
            last_reset = quota_row["last_reset_at"]
            
            # Reset if new month
            now = datetime.now()
            if last_reset and (now - last_reset).days >= 30:
                await conn.execute(
                    """
                    UPDATE user_quotas
                    SET tokens_used = 0, last_reset_at = $1
                    WHERE user_id = $2
                    """,
                    now,
                    user_id,
                )
                used = 0
            
            remaining = quota - used
            allowed = remaining > 0
            
            return (allowed, {
                "quota": quota,
                "used": used,
                "remaining": remaining,
            })
            
    except Exception as e:
        print(f"[Quota] Error checking quota: {e}")
        # Allow request on error (fail open)
        return (True, None)


async def increment_token_usage(user_id: str, tokens: int):
    """Increment token usage for user."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE user_quotas
                SET tokens_used = tokens_used + $1
                WHERE user_id = $2
                """,
                tokens,
                user_id,
            )
    except Exception as e:
        print(f"[Quota] Error incrementing usage: {e}")


async def quota_middleware(request: Request, call_next):
    """Middleware to check and enforce user quotas."""
    # Skip quota check for health and admin endpoints
    if request.url.path.startswith("/api/health") or request.url.path.startswith("/api/v1/admin"):
        return await call_next(request)
    
    # Get user ID from header (or default to anonymous)
    user_id = request.headers.get("X-User-ID", "anonymous")
    
    # Check quota
    allowed, quota_info = await check_user_quota(user_id)
    
    if not allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Quota exceeded",
                "message": "Monthly token quota exceeded. Please contact admin.",
                "quota": quota_info,
            },
        )
    
    # Process request
    response = await call_next(request)
    
    # Extract token usage from response headers (if available)
    tokens_used = response.headers.get("X-Tokens-Used")
    if tokens_used:
        try:
            await increment_token_usage(user_id, int(tokens_used))
        except ValueError:
            pass
    
    return response


