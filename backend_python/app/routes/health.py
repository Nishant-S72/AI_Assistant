"""Health check routes."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.db.connection import get_pool
from app.clients.llm import check_ollama_health
from app.clients.vectorstore.json_adapter import _json_store
from app.services.embeddings import get_embedding
from pathlib import Path
import os
import json

router = APIRouter()


@router.get("")
async def health():
    """Comprehensive health check endpoint."""
    health_status = {
        "status": "ok",
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }

    # Check database
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

    # Check embeddings service
    try:
        # Quick test embedding
        test_embedding = await get_embedding("test")
        health_status["embeddings_service"] = "reachable" if test_embedding and len(test_embedding) > 0 else "unavailable"
    except Exception:
        health_status["embeddings_service"] = "unavailable"

    # Check vectorstore
    try:
        chunk_count = len(_json_store.vectors)
        health_status["vectorstore"] = {
            "adapter": "json",
            "status": "ok" if chunk_count > 0 else "empty",
            "count_chunks": chunk_count,
        }
        
        # Try to get last_seeded_at from metadata
        metadata_path = Path(__file__).parent.parent.parent / "backend_python" / "storage" / "vector_metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                health_status["vectorstore"]["last_seeded_at"] = metadata.get("last_seeded_at")
    except Exception as e:
        health_status["vectorstore"] = {
            "adapter": "json",
            "status": "error",
            "error": str(e),
        }

    status_code = 200 if health_status["status"] == "ok" else 503
    return JSONResponse(content=health_status, status_code=status_code)


@router.get("/vectorstore")
async def health_vectorstore():
    """Vector store health check endpoint."""
    try:
        chunk_count = len(_json_store.vectors)
        
        # Get metadata
        metadata_path = Path(__file__).parent.parent.parent / "backend_python" / "storage" / "vector_metadata.json"
        last_seeded_at = None
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                last_seeded_at = metadata.get("last_seeded_at")
        
        return {
            "status": "ok" if chunk_count > 0 else "empty",
            "adapter": "json",
            "count_chunks": chunk_count,
            "last_seeded_at": last_seeded_at,
        }
    except Exception as e:
        return JSONResponse(
            content={
                "status": "down",
                "adapter": "json",
                "error": str(e),
            },
            status_code=503
        )

