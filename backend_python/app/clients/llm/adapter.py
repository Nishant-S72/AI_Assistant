"""Unified LLM adapter with streaming and fallback support."""
import os
from typing import AsyncIterator, List, Dict, Any, Optional
from .openai_adapter import LLMMessage, LLMResponse, LLMOptions
from .fallback_wrapper import call_with_fallback
from openai import AsyncOpenAI


async def stream_chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
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
        
        # Send done marker
        yield {"type": "done"}
        
    except Exception as e:
        yield {"type": "error", "text": str(e)}


async def summarize(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
) -> str:
    """
    Summarize a list of messages using LLM.
    
    Args:
        messages: List of message dicts
        model: Model name (defaults to OPENAI_MODEL)
    
    Returns:
        Summary string
    """
    from .fallback import generate_chat_completion, LLMRequestOptions
    
    messages_text = "\n".join([
        f"{msg.get('role', 'user')}: {msg.get('content', '')}"
        for msg in messages
    ])
    
    prompt = f"""Summarize the following conversation in 2-3 sentences, focusing on key points and decisions:

{messages_text}

Summary:"""
    
    try:
        response = await generate_chat_completion(
            LLMRequestOptions(
                model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    LLMMessage("system", "You are a helpful assistant that summarizes conversations concisely."),
                    LLMMessage("user", prompt),
                ],
                max_tokens=150,
                temperature=0.3,
            )
        )
        return response.content.strip()
    except Exception as e:
        print(f"Summarization error: {e}")
        return "Previous conversation context (summary unavailable)"


