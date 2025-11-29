"""Vector store adapters for RAG."""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Vector store result structure
@dataclass
class VectorQueryResult:
    """Result from vector store query."""
    id: str
    text: str
    score: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


async def query_vectorstore(query_text: str, k: int = 3) -> List[VectorQueryResult]:
    """
    Query vector store (Chroma or JSON fallback).
    Returns list of VectorQueryResult with id, text, score, metadata.
    """
    import os
    from .json_adapter import query_json_store
    
    # Try Chroma first if configured
    use_chroma = os.getenv("VECTORSTORE_MODE", "auto") != "json"
    
    if use_chroma:
        try:
            from .chroma_adapter import query_chroma, check_chroma_health
            if await check_chroma_health():
                return await query_chroma(query_text, k)
        except Exception as e:
            print(f"[VectorStore] Chroma failed, falling back to JSON: {e}")
    
    # Fallback to JSON
    return await query_json_store(query_text, k)

