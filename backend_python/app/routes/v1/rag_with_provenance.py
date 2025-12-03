"""RAG chat endpoint with provenance."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from app.clients.vectorstore.rag_with_provenance import retrieve_with_provenance, format_provenance
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
        chunks = await retrieve_with_provenance(
            request.query,
            top_k=request.top_k,
            chunk_size=request.chunk_size,
        )
        
        if not chunks:
            return {
                "response": "I couldn't find relevant information in the knowledge base.",
                "provenance": [],
            }
        
        # Build context from chunks
        context = "\n\n".join([
            f"[Source: {chunk.filename}]\n{chunk.text}"
            for chunk in chunks
        ])
        
        # Generate response with LLM
        prompt = f"""Based on the following knowledge base documents, answer the question.

Knowledge Base:
{context}

Question: {request.query}

Answer based on the documents above. If the documents don't contain the answer, say so."""
        
        response = await generate_chat_completion(
            LLMRequestOptions(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    LLMMessage("system", "You are a helpful assistant that answers questions based on provided documents."),
                    LLMMessage("user", prompt),
                ],
                max_tokens=500,
                temperature=0.3,
            )
        )
        
        # Format provenance
        provenance = format_provenance(chunks, top_n=3)
        
        return {
            "response": response.content,
            "provenance": provenance,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG chat error: {str(e)}")

