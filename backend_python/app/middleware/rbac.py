"""Role-based access control (RBAC) middleware."""
from fastapi import HTTPException, Depends, Request
from typing import Optional
from app.db.connection import get_pool


async def get_current_user(request: Request) -> dict:
    """
    Get current user from request header.
    
    TODO: Replace with JWT token validation
    """
    user_id = request.headers.get("X-User-ID") or "anonymous"
    
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            user_row = await conn.fetchrow(
                "SELECT id, role FROM users WHERE id = $1",
                user_id,
            )
            
            if not user_row:
                # Create default user with 'user' role
                await conn.execute(
                    "INSERT INTO users (id, role) VALUES ($1, 'user')",
                    user_id,
                )
                return {"id": user_id, "role": "user"}
            
            return {"id": user_row["id"], "role": user_row.get("role", "user")}
    except Exception as e:
        print(f"Error getting user: {e}")
        return {"id": user_id, "role": "user"}


async def require_admin_role(current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency to require admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return current_user


async def require_role(allowed_roles: list[str], current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency to require one of the allowed roles."""
    if current_user.get("role") not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Required role: {', '.join(allowed_roles)}",
        )
    return current_user

