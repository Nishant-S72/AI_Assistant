"""Admin endpoints for v1 API."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.db.connection import get_pool
from app.middleware.rbac import require_admin_role

router = APIRouter()


class UpdateQuotaRequest(BaseModel):
    """Request to update user quota."""
    monthly_quota_tokens: int


@router.patch("/users/{user_id}/quota")
async def update_user_quota(
    user_id: str,
    request: UpdateQuotaRequest,
    admin_user: dict = Depends(require_admin_role),
):
    """Update user's monthly token quota (admin only)."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE users
                SET monthly_quota_tokens = $1
                WHERE id = $2
                """,
                request.monthly_quota_tokens,
                user_id,
            )
            
            if result == "UPDATE 0":
                raise HTTPException(status_code=404, detail="User not found")
            
            return {"user_id": user_id, "monthly_quota_tokens": request.monthly_quota_tokens}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update quota: {str(e)}")


@router.get("/metrics")
async def get_metrics(admin_user: dict = Depends(require_admin_role)):
    """Get admin analytics metrics."""
    from app.services.metrics import get_metrics_service
    
    metrics_service = get_metrics_service()
    metrics = metrics_service.get_metrics()
    
    return metrics

