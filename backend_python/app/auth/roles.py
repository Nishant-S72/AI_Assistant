"""Role-based access control utilities."""
from fastapi import Depends, HTTPException, status
from app.middleware.rbac import get_current_user


def require_role(required_role: str):
    """
    Dependency to require a specific role.
    
    Usage:
        @router.get("/admin")
        async def admin_endpoint(user: dict = Depends(require_role("admin"))):
            ...
    """
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role", "user")
        
        # Role hierarchy: admin > user > read_only
        role_hierarchy = {
            "admin": 3,
            "user": 2,
            "read_only": 1,
        }
        
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}",
            )
        
        return current_user
    
    return role_checker


