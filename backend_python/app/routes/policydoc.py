"""Policy document routes."""
from fastapi import APIRouter
from typing import List, Dict, Any
from app.clients.vectorstore import query_vectorstore

router = APIRouter()


@router.get("/chunks")
async def get_policy_chunks():
    """Get available policy document chunks metadata."""
    try:
        # Query with a generic query to get all chunks (or sample)
        # In a real implementation, you'd maintain a chunks index
        # For now, return metadata about available chunks
        
        # Try to get chunks by querying with a broad term
        sample_chunks = await query_vectorstore("policy document", k=10)
        
        chunks_metadata = [
            {
                "id": chunk.id,
                "title": chunk.metadata.get("title", f"Policy Section {chunk.id[:8]}"),
                "summary": chunk.text[:150] + "..." if len(chunk.text) > 150 else chunk.text,
                "score": chunk.score,
            }
            for chunk in sample_chunks
        ]
        
        return {"chunks": chunks_metadata}
    except Exception as e:
        print(f"Error fetching policy chunks: {e}")
        # Return empty list if vector store unavailable
        return {"chunks": []}

