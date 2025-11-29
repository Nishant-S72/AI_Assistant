"""Chat routes."""
from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.agents.agentic_chat import run_agentic_chat

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    conversationHistory: Optional[List[Dict[str, str]]] = None
    sessionId: Optional[str] = None


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

