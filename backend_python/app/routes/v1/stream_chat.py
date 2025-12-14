"""Streaming chat endpoint (SSE)."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
from app.clients.llm.adapter import stream_chat

router = APIRouter()


class StreamChatRequest(BaseModel):
    """Request model for streaming chat."""
    messages: List[Dict[str, str]]
    model: Optional[str] = None
    conversation_id: Optional[str] = None


async def event_stream_generator(messages: List[Dict[str, str]], model: Optional[str]):
    """Generate SSE event stream from LLM tokens."""
    try:
        async for chunk in stream_chat(messages, model):
            # Format as SSE: data: {json}\n\n
            data = json.dumps(chunk)
            yield f"data: {data}\n\n"
    except Exception as e:
        error_chunk = {"type": "error", "text": str(e)}
        yield f"data: {json.dumps(error_chunk)}\n\n"


@router.post("/stream_chat")
async def stream_chat_endpoint(request: StreamChatRequest):
    """
    Stream chat completion using Server-Sent Events (SSE).
    
    Returns text/event-stream with JSON chunks:
    - {"type": "token", "text": "..."} for each token
    - {"type": "done", "text": "[DONE]"} when complete
    - {"type": "error", "text": "..."} on error
    """
    try:
        return StreamingResponse(
            event_stream_generator(request.messages, request.model),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Streaming error: {str(e)}")

