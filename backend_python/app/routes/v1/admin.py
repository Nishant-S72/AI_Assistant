"""Admin endpoints for v1 API."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.db.connection import get_pool
from app.auth.roles import require_role
from app.metrics.collector import get_metrics_collector

router = APIRouter()


class UpdateQuotaRequest(BaseModel):
    """Request to update user quota."""
    monthly_quota_tokens: int


@router.patch("/users/{user_id}/quota")
async def update_user_quota(
    user_id: str,
    quota: UpdateQuotaRequest,
    current_user: dict = Depends(require_role("admin")),
):
    """Update user's monthly token quota (admin only)."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Update or insert quota
            result = await conn.execute(
                """
                INSERT INTO user_quotas (user_id, monthly_quota_tokens, tokens_used, last_reset_at)
                VALUES ($1, $2, COALESCE((SELECT tokens_used FROM user_quotas WHERE user_id = $1), 0), CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE
                SET monthly_quota_tokens = $2, updated_at = CURRENT_TIMESTAMP
                """,
                user_id,
                quota.monthly_quota_tokens,
            )
            
            return {"user_id": user_id, "monthly_quota_tokens": quota.monthly_quota_tokens}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update quota: {str(e)}")


@router.get("/metrics")
async def get_metrics(current_user: dict = Depends(require_role("admin"))):
    """Get admin analytics metrics (admin only)."""
    metrics = get_metrics_collector()
    return metrics.get_metrics()

