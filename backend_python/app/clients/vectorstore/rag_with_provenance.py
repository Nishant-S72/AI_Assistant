"""RAG retriever with provenance metadata."""
from typing import List, Dict, Any, Optional
from app.clients.vectorstore.json_adapter import query_json_store, VectorQueryResult
import os


class RAGChunk:
    """RAG chunk with provenance metadata."""
    def __init__(
        self,
        text: str,
        score: float,
        source: Optional[str] = None,
        filename: Optional[str] = None,
        fragment_index: Optional[int] = None,
    ):
        self.text = text
        self.score = score
        self.source = source
        self.filename = filename
        self.fragment_index = fragment_index
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with provenance."""
        return {
            "text": self.text,
            "score": self.score,
            "source": self.source,
            "filename": self.filename,
            "fragment_index": self.fragment_index,
        }


async def retrieve_with_provenance(
    query: str,
    top_k: int = 5,
    chunk_size: Optional[int] = None,
) -> List[RAGChunk]:
    """
    Retrieve RAG chunks with provenance metadata.
    
    Args:
        query: Search query
        top_k: Number of chunks to return
        chunk_size: Configurable chunk size (TODO: implement)
    
    Returns:
        List of RAGChunk objects with metadata
    """
    # Get chunk size from settings (default 500)
    chunk_size = chunk_size or int(os.getenv("RAG_CHUNK_SIZE", "500"))
    
    # Query vector store
    results: List[VectorQueryResult] = await query_json_store(query, k=top_k)
    
    chunks = []
    for i, result in enumerate(results):
        # Extract metadata from result
        metadata = result.metadata if hasattr(result, 'metadata') else {}
        
        chunk = RAGChunk(
            text=result.text if hasattr(result, 'text') else str(result),
            score=result.score if hasattr(result, 'score') else 0.0,
            source=metadata.get("source", "unknown"),
            filename=metadata.get("filename", "unknown"),
            fragment_index=metadata.get("fragment_index", i),
        )
        chunks.append(chunk)
    
    return chunks


def format_provenance(chunks: List[RAGChunk], top_n: int = 3) -> List[Dict[str, Any]]:
    """Format provenance for response."""
    top_chunks = sorted(chunks, key=lambda x: x.score, reverse=True)[:top_n]
    return [
        {
            "source": chunk.source,
            "filename": chunk.filename,
            "fragment_index": chunk.fragment_index,
            "score": round(chunk.score, 3),
            "snippet": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
        }
        for chunk in top_chunks
    ]

