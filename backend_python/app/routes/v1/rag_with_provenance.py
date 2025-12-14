"""RAG chat endpoint with provenance."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from app.rag.retriever import retrieve_chunks, format_rag_response
from app.clients.llm import generate_chat_completion, LLMMessage, LLMRequestOptions
import os

router = APIRouter()


class RAGChatRequest(BaseModel):
    """Request model for RAG chat with provenance."""
    query: str
    top_k: int = 5
    chunk_size: Optional[int] = None


@router.post("/rag_chat")
async def rag_chat_with_provenance(request: RAGChatRequest):
    """
    RAG chat endpoint that returns provenance metadata.
    
    Returns response with provenance array listing top sources.
    """
    try:
        # Retrieve chunks with provenance
        chunks = await retrieve_chunks(
            query=request.query,
            top_k=request.top_k,
        )
        
        if not chunks:
            return {
                "response": "I couldn't find relevant information in the knowledge base.",
                "provenance": [],
            }
        
        # Format response with RAG
        response_text = await format_rag_response(
            chunks=chunks,
            query=request.query,
            tone="warm",
        )
        
        # Format provenance from chunks
        provenance = [
            {
                "source": chunk.get("source", "unknown"),
                "filename": chunk.get("filename", "unknown"),
                "fragment_index": chunk.get("fragment_index", 0),
                "score": round(chunk.get("score", 0.0), 3),
                "snippet": chunk.get("snippet", chunk.get("content", "")[:200]),
            }
            for chunk in chunks[:3]  # Top 3 for provenance
        ]
        
        return {
            "response": response_text,
            "provenance": provenance,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG chat error: {str(e)}")

