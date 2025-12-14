"""Conversation management endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.conversation_store import get_conversation_store
from app.conversation.summarizer import summarize_messages

router = APIRouter()


class ConversationResponse(BaseModel):
    """Response model for conversation."""
    id: str
    messages: list
    summary: Optional[str] = None


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation by ID."""
    store = get_conversation_store()
    conv = store.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.post("/{conversation_id}/regenerate_summary")
async def regenerate_summary(conversation_id: str):
    """Force regeneration of conversation summary."""
    store = get_conversation_store()
    try:
        summary = await store.regenerate_summary(conversation_id)
        return {"conversation_id": conversation_id, "summary": summary}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

