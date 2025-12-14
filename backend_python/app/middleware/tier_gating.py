"""
Tier gating middleware to enforce Assist vs Pro restrictions.
"""
from fastapi import Request, HTTPException
from typing import Callable, Optional
from app.core.config import UserTier, ASSIST_FORBIDDEN_ACTIONS
from app.core.errors import TierRestrictionError
from app.core.logger import logger
from app.db.connection import get_pool


async def get_user_tier(user_id: str) -> UserTier:
    """Get user tier from database."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Check if users table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'users'
                )
            """)
            
            if not table_exists:
                logger.warning("Users table does not exist, defaulting to assist tier", extra={"user_id": user_id})
                return UserTier.ASSIST
            
            row = await conn.fetchrow(
                "SELECT tier FROM users WHERE id = $1",
                user_id,
            )
            if row:
                tier_str = row.get("tier", "assist")
                return UserTier(tier_str) if tier_str in ["assist", "pro"] else UserTier.ASSIST
            # Default to assist if user not found
            return UserTier.ASSIST
    except Exception as e:
        logger.error(f"Error fetching user tier: {e}", extra={"user_id": user_id})
        # Default to assist on any error
        return UserTier.ASSIST


def check_tier_permission(tier: UserTier, action: str) -> bool:
    """Check if user tier allows the action."""
    if tier == UserTier.PRO:
        return True  # Pro can do everything
    
    if tier == UserTier.ASSIST:
        # Assist cannot perform forbidden actions
        return action not in ASSIST_FORBIDDEN_ACTIONS
    
    return False


async def tier_gating_middleware(
    request: Request,
    call_next: Callable,
    action: Optional[str] = None,
) -> Callable:
    """
    Middleware to enforce tier restrictions.
    
    Usage:
        @router.post("/execute")
        @tier_gating_middleware(action="auto_send_emails")
        async def execute_action(...):
            ...
    """
    # Extract user_id from header or request
    user_id = request.headers.get("X-User-ID") or request.state.get("user_id")
    
    if not user_id:
        # For development, allow if no user_id provided
        # In production, this should require authentication
        user_id = "default-user"
    
    if action:
        tier = await get_user_tier(user_id)
        
        if not check_tier_permission(tier, action):
            logger.warning(
                f"Tier restriction: {action} not allowed for tier {tier.value}",
                extra={"user_id": user_id, "tier": tier.value, "action": action}
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "TIER_RESTRICTION",
                    "message": f"This action requires Pro tier. Current tier: {tier.value}",
                    "current_tier": tier.value,
                    "required_tier": "pro",
                    "action": action,
                }
            )
    
    response = await call_next(request)
    return response


def require_tier(action: str):
    """Decorator to require specific tier for an endpoint."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract user_id from request or kwargs
            request = kwargs.get("request") or (args[0] if args else None)
            user_id = None
            
            if request and hasattr(request, "headers"):
                user_id = request.headers.get("X-User-ID")
            
            if not user_id:
                # Try to get from kwargs
                user_id = kwargs.get("user_id")
            
            if not user_id:
                raise HTTPException(status_code=401, detail="User ID required")
            
            tier = await get_user_tier(user_id)
            
            if not check_tier_permission(tier, action):
                raise TierRestrictionError(action, tier.value)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

