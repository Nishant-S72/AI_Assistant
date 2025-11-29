"""Admin routes."""
from fastapi import APIRouter, HTTPException, Depends, Query, Header
from typing import Optional
from app.db.connection import get_pool

router = APIRouter()


async def require_auth(authorization: Optional[str] = Header(None), token: Optional[str] = Query(None)):
    """Auth middleware."""
    import os
    auth_token = authorization.replace("Bearer ", "") if authorization else token
    expected_token = os.getenv("DEMO_SEED_TOKEN") or os.getenv("ADMIN_API_KEY")

    if not expected_token or auth_token != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return auth_token


@router.get("/audit")
async def get_audit_logs(
    limit: int = Query(50),
    offset: int = Query(0),
    _: str = Depends(require_auth),
):
    """Get audit logs."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT 
                    id,
                    type,
                    correlation_id,
                    request_path,
                    user_id,
                    prompt_ref,
                    retrieved_ids,
                    raw_model_response,
                    final_text,
                    latency_ms,
                    payload,
                    created_at
                FROM events
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )

            total_row = await conn.fetchrow("SELECT COUNT(*) as total FROM events")
            total = int(total_row["total"]) if total_row else 0

            return {
                "events": [dict(row) for row in rows],
                "total": total,
                "limit": limit,
                "offset": offset,
            }
    except Exception as error:
        print(f"Error fetching audit logs: {error}")
        raise HTTPException(status_code=500, detail="Failed to fetch audit logs")


@router.get("/metrics")
async def get_metrics(_: str = Depends(require_auth)):
    """Get metrics."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Suggestions generated
            suggestions_row = await conn.fetchrow("SELECT COUNT(*) as count FROM suggestions")
            suggestions_generated = int(suggestions_row["count"]) if suggestions_row else 0

            # Acceptance rate
            accepted_row = await conn.fetchrow(
                """
                SELECT COUNT(*) as count 
                FROM suggestions 
                WHERE final_text IS NOT NULL 
                AND final_text = model_response 
                AND edited = false
                """
            )
            accepted = int(accepted_row["count"]) if accepted_row else 0
            acceptance_rate = accepted / suggestions_generated if suggestions_generated > 0 else 0

            # Average latency
            latency_row = await conn.fetchrow(
                """
                SELECT AVG(latency_ms) as avg_latency 
                FROM events 
                WHERE latency_ms IS NOT NULL 
                AND type = 'suggestion_generated'
                """
            )
            avg_latency = (
                round(float(latency_row["avg_latency"])) if latency_row and latency_row["avg_latency"] else None
            )

            # Messages sent
            sent_row = await conn.fetchrow("SELECT COUNT(*) as count FROM events WHERE type = 'message_sent'")
            messages_sent = int(sent_row["count"]) if sent_row else 0

            return {
                "suggestionsGenerated": suggestions_generated,
                "acceptanceRate": round(acceptance_rate * 100) / 100,
                "avgLatencyMs": avg_latency,
                "messagesSent": messages_sent,
            }
    except Exception as error:
        print(f"Error fetching metrics: {error}")
        raise HTTPException(status_code=500, detail="Failed to fetch metrics")

