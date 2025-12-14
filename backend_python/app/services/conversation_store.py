"""Conversation memory and summarization service."""
from typing import List, Dict, Any, Optional
from app.conversation.summarizer import summarize_messages
import os


class ConversationStore:
    """Manages conversation memory with auto-summarization."""
    
    MAX_MESSAGES = 30
    TOKEN_THRESHOLD = 4000  # Approximate token threshold
    
    def __init__(self):
        self._conversations: Dict[str, Dict[str, Any]] = {}
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID."""
        return self._conversations.get(conversation_id)
    
    def add_message(self, conversation_id: str, role: str, content: str):
        """Add message to conversation."""
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = {
                "id": conversation_id,
                "messages": [],
                "summary": None,
            }
        
        conv = self._conversations[conversation_id]
        conv["messages"].append({"role": role, "content": content})
        
        # Check if summarization needed
        if len(conv["messages"]) > self.MAX_MESSAGES:
            self._auto_summarize(conversation_id)
    
    async def _auto_summarize(self, conversation_id: str):
        """Auto-summarize conversation when threshold exceeded."""
        conv = self._conversations.get(conversation_id)
        if not conv or len(conv["messages"]) <= self.MAX_MESSAGES:
            return
        
        # Keep recent messages, summarize older ones
        recent_count = 10
        recent_messages = conv["messages"][-recent_count:]
        old_messages = conv["messages"][:-recent_count]
        
        # Generate summary of old messages
        summary = await self._summarize_messages(old_messages)
        
        # Replace old messages with summary placeholder
        conv["messages"] = [
            {"role": "system", "content": f"[Previous conversation summary: {summary}]"}
        ] + recent_messages
        
        conv["summary"] = summary
    
    async def _summarize_messages(self, messages: List[Dict[str, str]]) -> str:
        """Summarize a list of messages using LLM."""
        try:
            return await summarize_messages(messages)
        except Exception as e:
            print(f"Summarization error: {e}")
            return "Previous conversation context (summary unavailable)"
    
    async def regenerate_summary(self, conversation_id: str) -> str:
        """Force regeneration of conversation summary."""
        conv = self._conversations.get(conversation_id)
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Summarize all messages except the most recent
        if len(conv["messages"]) > 1:
            messages_to_summarize = conv["messages"][:-1]
            summary = await self._summarize_messages(messages_to_summarize)
            conv["summary"] = summary
            return summary
        return "No messages to summarize"


# Global store instance
_store = ConversationStore()


def get_conversation_store() -> ConversationStore:
    """Get global conversation store."""
    return _store

