"""Conversation summarization service."""
from typing import List, Dict, Any
from app.clients.llm.adapter import summarize


async def summarize_messages(messages: List[Dict[str, str]]) -> str:
    """
    Summarize a list of messages using LLM.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
    
    Returns:
        Summary string
    """
    return await summarize(messages)


