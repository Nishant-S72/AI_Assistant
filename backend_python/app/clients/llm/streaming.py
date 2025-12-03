"""Streaming LLM client for SSE responses."""
import os
from typing import AsyncIterator, List, Dict, Any
from openai import AsyncOpenAI
from .openai_adapter import LLMMessage


async def stream_chat(
    messages: List[Dict[str, str]],
    model: str = None,
) -> AsyncIterator[Dict[str, Any]]:
    """
    Stream chat completion tokens.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model name (defaults to OPENAI_MODEL)
    
    Yields:
        Dict with 'type' and 'text' keys for each token
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not configured")
    
    model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = AsyncOpenAI(api_key=api_key)
    
    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield {"type": "token", "text": delta.content}
        
        # Send [DONE] marker
        yield {"type": "done", "text": "[DONE]"}
        
    except Exception as e:
        yield {"type": "error", "text": str(e)}

