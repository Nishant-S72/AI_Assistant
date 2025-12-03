"""Conversation context management for chat using state machine pattern."""
from typing import List, Dict, Any, Optional
from app.clients.llm import generate_chat_completion, LLMMessage, LLMRequestOptions
import os
import json
from datetime import datetime


class ConversationContextManager:
    """Manages conversation context using a state machine pattern."""
    
    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    async def _extract_entities(
        self, 
        messages: List[Dict[str, str]], 
        current_query: str
    ) -> Dict[str, Any]:
        """Extract entities (like country names) from conversation history."""
        # Get last few messages for context
        recent_messages = messages[-5:] if len(messages) > 5 else messages
        
        # Build context for entity extraction
        context_text = ""
        for msg in recent_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                context_text += f"User: {content}\n"
            elif role == "assistant":
                context_text += f"Assistant: {content}\n"
        
        # Let LLM do all the work - extract entities and determine context needs
        extraction_prompt = f"""Analyze the conversation context and current query. Determine:
1. What entities are mentioned (countries, topics, subjects)
2. Whether the current query references previous messages or introduces a new topic
3. If it's a follow-up question, what the complete question should be

Conversation context:
{context_text}

Current query: {current_query}

Return a JSON object with:
- "countries": [list of country names mentioned - prioritize countries from current query if present]
- "topics": [list of topics being discussed]
- "main_subject": the primary subject the user is asking about
- "needs_context": true if the current query is a follow-up that needs previous context
- "complete_query": the full, complete question combining context if needed (e.g., "culture of India" if user said "about the culture" after asking about India, or "Germany" if user said "what about Germany?" after asking about India)

IMPORTANT: If the current query mentions a NEW country/topic, treat it as a topic switch and use that country in complete_query. Don't combine with previous context.

Return only valid JSON:"""

        try:
            response = await generate_chat_completion(
                LLMRequestOptions(
                    model=self.model,
                    messages=[
                        LLMMessage("user", extraction_prompt),
                    ],
                    max_tokens=200,
                    temperature=0.3,
                    use_local=False,
                )
            )
            entities_text = response.content.strip()
            
            # Try to parse JSON (might be wrapped in markdown code blocks)
            if "```json" in entities_text:
                entities_text = entities_text.split("```json")[1].split("```")[0].strip()
            elif "```" in entities_text:
                entities_text = entities_text.split("```")[1].split("```")[0].strip()
            
            entities = json.loads(entities_text)
            # Ensure complete_query is set
            if "complete_query" not in entities:
                entities["complete_query"] = entities.get("main_subject") or current_query
        except Exception as e:
            print(f"[Context] Error extracting entities: {e}")
            entities = {
                "countries": [],
                "topics": [],
                "main_subject": None,
                "needs_context": False,
                "complete_query": current_query,
            }
        
        return entities
    
    def _combine_context(
        self, 
        current_query: str, 
        entities: Dict[str, Any]
    ) -> str:
        """Use LLM-determined complete query, fallback to current query."""
        # Let the LLM's complete_query be the source of truth
        complete_query = entities.get("complete_query")
        if complete_query and complete_query.strip():
            print(f"[Context] Using LLM-determined query: '{complete_query}' (original: '{current_query}')")
            return complete_query.strip()
        
        # Fallback to current query if LLM didn't provide complete_query
        return current_query
    
    def _classify_intent(self, entities: Dict[str, Any]) -> str:
        """Classify intent based on entities."""
        # Simple intent classification based on entities
        # Countries in query -> likely policy_intent (RAG for countries knowledge)
        countries = entities.get("countries", [])
        
        if countries:
            # If asking about countries, use RAG
            return "policy_intent"
        else:
            # Default to general intent (will be refined by main intent classifier)
            return "general_intent"
    
    async def process_query(
        self, 
        user_message: str, 
        thread_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Process a user query with conversation context using state machine pattern."""
        # Build messages list from history
        messages = conversation_history or []
        
        # Let LLM extract entities and determine complete query
        entities = await self._extract_entities(messages, user_message)
        
        # Use LLM-determined complete query
        combined_query = self._combine_context(user_message, entities)
        
        # Step 4: Classify intent
        intent = self._classify_intent(entities)
        
        return {
            "combined_query": combined_query,
            "extracted_entities": entities,
            "intent": intent,
            "messages": messages,
        }


# Global instance
_context_manager: Optional[ConversationContextManager] = None


def get_context_manager() -> ConversationContextManager:
    """Get or create the global conversation context manager."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ConversationContextManager()
    return _context_manager

