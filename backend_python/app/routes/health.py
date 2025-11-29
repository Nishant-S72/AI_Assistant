"""Health check routes."""
from fastapi import APIRouter, HTTPException
from app.db.connection import get_pool
from app.clients.llm import check_ollama_health
import os

router = APIRouter()


@router.get("")
async def health():
    """Health check endpoint."""
    health_status = {
        "status": "ok",
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        health_status["database"] = "connected"
    except Exception:
        health_status["database"] = "disconnected"
        health_status["status"] = "degraded"

    # Check LLM availability
    try:
        use_ollama = os.getenv("USE_OLLAMA") != "false"
        if use_ollama:
            health_status["llm"] = (
                "ollama_available" if await check_ollama_health() else "ollama_unavailable"
            )
        elif os.getenv("OPENAI_API_KEY"):
            health_status["llm"] = "openai_configured"
        else:
            health_status["llm"] = "not_configured"
    except Exception:
        health_status["llm"] = "unknown"

    status_code = 200 if health_status["status"] == "ok" else 503
    return health_status

