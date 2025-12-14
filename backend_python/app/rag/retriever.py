"""
RAG retriever - retrieves top K chunks with citations.
"""
from typing import List, Dict, Any, Optional
from app.core.config import RAG_TOP_K
from app.core.errors import RAGError
from app.core.logger import logger
from app.clients.vectorstore.json_adapter import query_json_store
from app.clients.vectorstore import VectorQueryResult
from typing import List as TypingList


async def retrieve_chunks(
    query: str,
    top_k: int = RAG_TOP_K,
    correlation_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve top K chunks for a query.
    
    Returns:
        List of chunks with metadata:
        {
            "content": str,
            "source": str,
            "filename": str,
            "fragment_index": int,
            "score": float,
            "snippet": str,
        }
    """
    try:
        logger.info(
            "RAG retrieval started",
            extra={
                "query": query[:100],  # Truncate for logging
                "top_k": top_k,
                "correlation_id": correlation_id,
            }
        )
        
        # Query vector store
        results: TypingList[VectorQueryResult] = await query_json_store(query, k=top_k)
        
        chunks = []
        for idx, result in enumerate(results, 1):
            # Extract metadata
            metadata = result.metadata if result.metadata else {}
            text = result.text
            score = result.score
            
            chunks.append({
                "content": text,
                "source": metadata.get("source", "unknown"),
                "filename": metadata.get("filename", "unknown"),
                "fragment_index": metadata.get("fragment_index", idx - 1),
                "score": score,
                "snippet": text[:200] + "..." if len(text) > 200 else text,
                "citation_token": f"[ref{idx}]",
            })
        
        logger.info(
            "RAG retrieval completed",
            extra={
                "chunks_found": len(chunks),
                "correlation_id": correlation_id,
            }
        )
        
        return chunks
        
    except Exception as e:
        logger.error(f"RAG retrieval failed: {e}", extra={"correlation_id": correlation_id})
        raise RAGError(f"Failed to retrieve chunks: {str(e)}")


async def format_rag_response(
    chunks: List[Dict[str, Any]],
    query: str,
    tone: str = "warm",
    correlation_id: Optional[str] = None,
) -> str:
    """
    Format RAG response with citations.
    
    Args:
        chunks: Retrieved chunks
        query: User query
        tone: Response tone (formal/warm/crisp)
        correlation_id: Optional correlation ID
    
    Returns:
        Formatted response with citation tokens
    """
    if not chunks:
        return "I don't have information about that in the available documents."
    
    # Build context from chunks
    context_parts = []
    for chunk in chunks:
        citation = chunk.get("citation_token", "")
        context_parts.append(f"{citation} {chunk.get('content', '')}")
    
    context = "\n\n".join(context_parts)
    
    # Load RAG prompt
    from app.llm.provider import load_prompt, run_llm
    
    rag_prompt = load_prompt("rag_prompt")
    
    # Build full prompt
    full_prompt = f"""User question: {query}

Retrieved chunks:
{context}

Answer the question using the chunks above. Include citation tokens [ref1], [ref2], [ref3] when referencing information from chunks.

Tone: {tone}"""
    
    try:
        response = await run_llm(
            task="rag_answer_synthesis",
            prompt=full_prompt,
            system_prompt=rag_prompt,
            temperature=0.7,
            max_tokens=500,
            correlation_id=correlation_id,
        )
        
        return response
        
    except Exception as e:
        logger.error(f"RAG response formatting failed: {e}", extra={"correlation_id": correlation_id})
        # Fallback: return chunks directly
        return "\n\n".join([
            f"{chunk.get('citation_token', '')} {chunk.get('content', '')}"
            for chunk in chunks[:3]
        ])
