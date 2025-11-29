"""Chat routes."""
from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel
from app.agents.agentic_chat import run_agentic_chat
from app.clients.vectorstore import query_vectorstore, VectorQueryResult
from app.clients.llm import generate_chat_completion, LLMMessage, LLMRequestOptions
from app.policy.policy_engine import check_policy
from app.db.connection import get_pool
from pathlib import Path
import os
import uuid
import json
import gzip
from datetime import datetime

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    conversationHistory: Optional[List[Dict[str, str]]] = None
    sessionId: Optional[str] = None


class RAGChatRequest(BaseModel):
    """Request for RAG-enabled chat."""
    threadId: Optional[str] = None
    userMessage: str
    tone: Optional[Literal["formal", "warm", "crisp"]] = "warm"
    rag: bool = True


class ChatFeedbackRequest(BaseModel):
    """Feedback for chat suggestions."""
    suggestionId: str
    accepted: bool
    editedText: Optional[str] = None


@router.post("")
async def chat(request: ChatRequest):
    """Answer questions about inbox, policies, tasks, and create calendar events."""
    try:
        if not request.question or not isinstance(request.question, str):
            raise HTTPException(status_code=400, detail="Question is required")

        # Use agentic chat agent
        try:
            agent_session_id = request.sessionId or f"agent_{__import__('time').time()}_{__import__('uuid').uuid4().hex[:9]}"
            result = await run_agentic_chat(
                request.question,
                agent_session_id,
                request.conversationHistory or [],
            )

            return {
                "answer": result["answer"],
                "model": __import__("os").getenv("LLM_MODEL") or "tinyllama",
                "calendarEvent": result.get("calendarEvent"),
                "sessionId": result.get("sessionId", agent_session_id),
            }
        except Exception as agent_error:
            print(f"[Chat] Agentic chat error: {agent_error}")
            # Fallback to simple response
            return {
                "answer": "I'm having trouble processing that request. Please try again.",
                "model": __import__("os").getenv("LLM_MODEL") or "tinyllama",
                "sessionId": request.sessionId,
            }
    except HTTPException:
        raise
    except Exception as error:
        print(f"Error in chat: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to process chat: {str(error)}")


@router.post("/rag")
async def rag_chat(request: RAGChatRequest):
    """RAG-enabled chat with policy document retrieval."""
    try:
        if not request.userMessage or not isinstance(request.userMessage, str):
            raise HTTPException(status_code=400, detail="userMessage is required")
        
        correlation_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        # Check policy safety
        policy_check = check_policy(request.userMessage)
        if policy_check["action"] == "ESCALATE":
            return {
                "reply": "This request requires human review due to sensitive content. I'm escalating this to a human reviewer.",
                "citations": [],
                "suggestionId": None,
                "escalated": True,
                "reasons": [r["reason"] for r in policy_check.get("reasons", [])]
            }
        
        # Retrieve policy chunks if RAG enabled
        retrieved_chunks: List[VectorQueryResult] = []
        if request.rag:
            try:
                retrieved_chunks = await query_vectorstore(request.userMessage, k=3)
            except Exception as e:
                print(f"[RAG] Vector store query failed: {e}")
                # Continue without RAG if vector store fails
        
        # Build prompt from template
        prompt_template_path = Path(__file__).parent.parent.parent.parent / "prompts" / "policy_chat_template.md"
        if not prompt_template_path.exists():
            # Try alternative paths
            alt_paths = [
                Path(__file__).parent.parent.parent / "prompts" / "policy_chat_template.md",
                Path.cwd() / "prompts" / "policy_chat_template.md",
            ]
            for alt_path in alt_paths:
                if alt_path.exists():
                    prompt_template_path = alt_path
                    break
        
        if prompt_template_path.exists():
            template = prompt_template_path.read_text(encoding="utf-8")
        else:
            # Fallback template
            template = """You are Soraya, an AI assistant. Answer questions concisely.
            
Policy Context:
{retrieved_chunks}

Conversation:
{conversation}

User: {user_message}
Assistant:"""
        
        # Format retrieved chunks
        chunks_text = ""
        if retrieved_chunks:
            chunks_text = "\n\n".join([
                f"§{i+1}. {chunk.text[:200]}... (ID: {chunk.id}, Score: {chunk.score:.2f})"
                for i, chunk in enumerate(retrieved_chunks)
            ])
        else:
            chunks_text = "No relevant policy chunks found."
        
        # Format conversation history
        conversation_text = "No previous messages."
        if request.threadId:
            # TODO: Load conversation history from DB if threadId provided
            conversation_text = "Previous conversation context available."
        
        # Build final prompt
        system_prompt = template.format(
            persona="You are Soraya, a helpful AI assistant.",
            tone=request.tone or "warm",
            retrieved_chunks=chunks_text,
            conversation=conversation_text,
            user_message=request.userMessage
        )
        
        # Truncate prompt if too long (keep last 4000 chars)
        if len(system_prompt) > 4000:
            system_prompt = system_prompt[-4000:]
        
        # Save prompt snapshot (truncated)
        prompt_snapshot = system_prompt[:4000]
        suggestion_id = str(uuid.uuid4())
        
        # Save gzipped prompt
        storage_dir = Path(__file__).parent.parent.parent.parent / "backend" / "storage" / "prompts"
        if not storage_dir.exists():
            storage_dir = Path.cwd() / "backend_python" / "storage" / "prompts"
            storage_dir.mkdir(parents=True, exist_ok=True)
        
        gzip_path = storage_dir / f"{suggestion_id}.gz"
        try:
            with gzip.open(gzip_path, "wt", encoding="utf-8") as f:
                f.write(system_prompt)
        except Exception as e:
            print(f"[RAG] Failed to save gzipped prompt: {e}")
        
        # Call LLM
        try:
            llm_response = await generate_chat_completion(
                LLMRequestOptions(
                    model=os.getenv("LLM_MODEL", "tinyllama"),
                    messages=[
                        LLMMessage("system", system_prompt),
                        LLMMessage("user", request.userMessage),
                    ],
                    max_tokens=250,
                    temperature=0.7,
                    use_local=os.getenv("USE_OLLAMA") != "false",
                    correlation_id=correlation_id,
                )
            )
            
            reply = llm_response.content.strip()
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Save to audit table
            try:
                pool = await get_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO suggestions (id, prompt, retrieved_ids, model_response, final_text)
                        VALUES ($1, $2, $3, $4, $5)
                        """,
                        suggestion_id,
                        prompt_snapshot,
                        json.dumps([chunk.id for chunk in retrieved_chunks]),
                        reply,
                        reply,
                    )
                    
                    await conn.execute(
                        """
                        INSERT INTO events (type, correlation_id, prompt_ref, retrieved_ids, raw_model_response, final_text, latency_ms)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                        "rag_chat",
                        correlation_id,
                        str(gzip_path),
                        json.dumps([chunk.id for chunk in retrieved_chunks]),
                        reply,
                        reply,
                        latency_ms,
                    )
            except Exception as e:
                print(f"[RAG] Failed to save to audit: {e}")
            
            # Format citations
            citations = [
                {
                    "id": chunk.id,
                    "score": chunk.score,
                    "textSnippet": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text
                }
                for chunk in retrieved_chunks
            ]
            
            return {
                "reply": reply,
                "citations": citations,
                "suggestionId": suggestion_id,
                "escalated": False,
            }
            
        except Exception as e:
            print(f"[RAG] LLM call failed: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate response: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as error:
        print(f"Error in RAG chat: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to process RAG chat: {str(error)}")


@router.post("/feedback")
async def chat_feedback(request: ChatFeedbackRequest):
    """Save feedback for chat suggestions."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Update suggestion
            await conn.execute(
                """
                UPDATE suggestions 
                SET final_text = $1, edited = $2, edit_diff = $3
                WHERE id = $4
                """,
                request.editedText if request.editedText else None,
                not request.accepted or (request.editedText is not None),
                request.editedText if request.editedText else None,
                request.suggestionId,
            )
            
            # Log feedback event
            await conn.execute(
                """
                INSERT INTO events (type, payload)
                VALUES ($1, $2)
                """,
                "chat_feedback",
                json.dumps({
                    "suggestionId": request.suggestionId,
                    "accepted": request.accepted,
                    "edited": request.editedText is not None,
                }),
            )
        
        return {"success": True}
    except Exception as error:
        print(f"Error saving feedback: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to save feedback: {str(error)}")

