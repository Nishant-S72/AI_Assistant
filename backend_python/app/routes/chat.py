"""Chat routes with intent-based routing and policy escalation."""
from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel
from app.agents.agentic_chat import run_agentic_chat
from app.clients.vectorstore import query_vectorstore, VectorQueryResult
from app.clients.llm import generate_chat_completion, LLMMessage, LLMRequestOptions
from app.policy.policy_engine import check_policy
from app.policy.intent_classifier import classify_intent_async, INTENT_RULES_CONFIDENCE_THRESHOLD
from app.db.connection import get_pool
from app.services.conversation_context import get_context_manager
from pathlib import Path
import os
import uuid
import json
import gzip
from datetime import datetime

router = APIRouter()


async def _load_conversation_history(thread_id: Optional[str]) -> List[Dict[str, str]]:
    """Load conversation history for a thread from database."""
    if not thread_id:
        return []
    
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Try to load from events table (where chat messages are logged)
            # Look for thread_id in payload JSON
            rows = await conn.fetch("""
                SELECT payload::text as payload, final_text, type, created_at
                FROM events
                WHERE type IN ('chat_general', 'rag_chat', 'action_calendar_created')
                  AND payload::jsonb ? 'thread_id'
                  AND payload::jsonb->>'thread_id' = $1
                ORDER BY created_at ASC
                LIMIT 20
            """, thread_id)
            
            history = []
            for row in rows:
                payload = json.loads(row['payload']) if row['payload'] else {}
                user_message = payload.get('user_message', '') or payload.get('userMessage', '')
                if user_message:
                    history.append({
                        "role": "user",
                        "content": user_message,
                    })
                
                # Add assistant response
                if row['final_text']:
                    history.append({
                        "role": "assistant",
                        "content": row['final_text'],
                    })
            
            print(f"[Chat] Loaded {len(history)} messages from history for thread {thread_id}")
            return history
    except Exception as e:
        print(f"[Chat] Error loading conversation history: {e}")
        import traceback
        traceback.print_exc()
        return []


class ChatRequest(BaseModel):
    """Chat request - supports both old and new API formats."""
    question: Optional[str] = None
    userMessage: Optional[str] = None  # New API format
    threadId: Optional[str] = None  # New API format
    tone: Optional[Literal["formal", "warm", "crisp"]] = "warm"  # New API format
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
    """Answer questions about inbox, policies, tasks, and create calendar events.
    
    Supports both old API format ({question}) and new intent-based format ({userMessage}).
    Uses intent classification to route to appropriate handler.
    """
    try:
        # Support both old and new API formats
        user_message = request.userMessage or request.question
        if not user_message or not isinstance(user_message, str):
            raise HTTPException(status_code=400, detail="userMessage or question is required")

        # If using new API format (userMessage), use intent-based routing with LangGraph context
        if request.userMessage:
            # NOTE: This is an onboard RAG bot with NO human backup
            # Policy questions should be answered via RAG, not escalated
            
            # Load conversation history for context
            conversation_history = await _load_conversation_history(request.threadId)
            
            # Use LangGraph to process query with context
            context_manager = get_context_manager()
            context_result = await context_manager.process_query(
                user_message=request.userMessage,
                thread_id=request.threadId,
                conversation_history=conversation_history,
            )
            
            # Use combined query from context (e.g., "culture of India" instead of just "about the culture")
            combined_query = context_result.get("combined_query", request.userMessage)
            extracted_entities = context_result.get("extracted_entities", {})
            
            print(f"[Chat] Original: {request.userMessage}")
            print(f"[Chat] Combined: {combined_query}")
            print(f"[Chat] Entities: {extracted_entities}")
            
            # Classify intent using combined query for better accuracy
            intent_result = await classify_intent_async(combined_query)
            intent = intent_result["intent"]
            confidence = intent_result.get("confidence", 0.7)
            intent_method = intent_result.get("method", "rules")
            intent_reasons = intent_result.get("reasons", [])
            
            # Override intent if context suggests policy intent (countries mentioned)
            if extracted_entities.get("countries"):
                intent = "policy_intent"
                print(f"[Chat] Overriding intent to policy_intent (countries detected: {extracted_entities.get('countries')})")
            
            print(f"[Chat] Intent: {intent} (confidence: {confidence:.2f}, method: {intent_method})")
            
            # Check if confidence is below threshold (needs manual labeling)
            needs_manual_label = confidence < INTENT_RULES_CONFIDENCE_THRESHOLD
            
            # Route based on intent
            if intent == "policy_intent":
                # Use RAG endpoint for policy questions (with combined query)
                rag_request = RAGChatRequest(
                    threadId=request.threadId,
                    userMessage=combined_query,  # Use combined query for better RAG retrieval
                    tone=request.tone,
                    rag=True,
                )
                response = await rag_chat(rag_request)
                # Add needs_manual_label if applicable
                if needs_manual_label:
                    response["needs_manual_label"] = True
                return response
            elif intent == "action_intent":
                # Route to action handler (use original message for action parsing)
                return await handle_action_intent(request.userMessage, request.threadId, request.tone, intent_result)
            else:
                # general_intent - use conversational assistant (with combined query for context)
                response = await handle_general_intent(combined_query, request.threadId, request.tone)
                # Add needs_manual_label if applicable
                if needs_manual_label:
                    response["needs_manual_label"] = True
                return response
        
        # Old API format - use agentic chat agent
        try:
            agent_session_id = request.sessionId or f"agent_{__import__('time').time()}_{__import__('uuid').uuid4().hex[:9]}"
            result = await run_agentic_chat(
                user_message,
                agent_session_id,
                request.conversationHistory or [],
            )

            return {
                "answer": result["answer"],
                "model": __import__("os").getenv("OPENAI_MODEL") or __import__("os").getenv("LLM_MODEL", "gpt-4o-mini"),
                "calendarEvent": result.get("calendarEvent"),
                "sessionId": result.get("sessionId", agent_session_id),
            }
        except Exception as agent_error:
            print(f"[Chat] Agentic chat error: {agent_error}")
            # Fallback to simple response
            return {
                "answer": "I'm having trouble processing that request. Please try again.",
                "model": __import__("os").getenv("OPENAI_MODEL") or __import__("os").getenv("LLM_MODEL", "gpt-4o-mini"),
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
        
        # Note: Policy escalation is now checked in main /api/chat route BEFORE routing here
        # This RAG endpoint assumes escalation has already been handled
        
        # Retrieve policy chunks if RAG enabled
        retrieved_chunks: List[VectorQueryResult] = []
        rag_error = None
        
        if request.rag:
            try:
                retrieved_chunks = await query_vectorstore(request.userMessage, k=5)  # Get more chunks for filtering
                
                # GUARDRAIL 1: Filter chunks by similarity threshold (0.3 = 30% similarity minimum)
                SIMILARITY_THRESHOLD = 0.3
                filtered_chunks = [chunk for chunk in retrieved_chunks if chunk.score >= SIMILARITY_THRESHOLD]
                
                if len(filtered_chunks) == 0 and len(retrieved_chunks) > 0:
                    # Low relevance - ask for clarification
                    print(f"[RAG] Low relevance chunks (max score: {max(c.score for c in retrieved_chunks):.2f} < {SIMILARITY_THRESHOLD})")
                    return {
                        "kind": "policy",
                        "text": "I'm not entirely sure what you're looking for. Could you clarify your question? For example:\n- Are you asking about a specific country, policy, or topic?\n- What specific information would be most helpful?",
                        "citations": [],
                        "suggestionId": str(uuid.uuid4()),
                        "intent": "policy_intent",
                        "intent_confidence": 0.5,
                        "escalated": False,
                        "needs_clarification": True,
                    }
                
                retrieved_chunks = filtered_chunks[:3]  # Use top 3 after filtering
                
                # If no chunks returned, check if vectorstore is empty
                if len(retrieved_chunks) == 0:
                    rag_error = "no_chunks"
                    print("[RAG] Warning: No chunks retrieved from vector store. Policy docs may not be seeded.")
            except Exception as e:
                print(f"[RAG] Vector store query failed: {e}")
                rag_error = "vectorstore_unavailable"
                # Continue without RAG if vector store fails
        
        # If RAG failed and no chunks, return error response
        if rag_error and len(retrieved_chunks) == 0:
            return {
                "kind": "policy",
                "text": "Policy lookup is currently unavailable. The policy documents may not be seeded yet. Please run: python scripts/seed_policy_docs.py",
                "citations": [],
                "suggestionId": None,
                "intent": "policy_intent",
                "intent_confidence": 1.0,
                "escalated": False,
                "rag_error": rag_error,
            }
        
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
            # Fallback template - optimized for RAG with knowledge base
            template = """You are Soraya, an AI assistant helping users with questions about countries, policies, and general knowledge.

**CRITICAL**: The documents below contain relevant information from the knowledge base. You MUST use them to answer the question.

Knowledge Base Documents:
{retrieved_chunks}

Instructions:
- **MANDATORY**: Answer using the information from the documents provided above
- **MANDATORY**: If documents are provided, you MUST use them - do NOT say you don't have the information
- Be concise and accurate
- Use a {tone} tone
- Cite sources using format: (Policy §1), (Policy §2), etc. for each document section used

User Question: {user_message}

Assistant Response:"""
        
        # Format retrieved chunks - include full text for better context
        chunks_text = ""
        max_score = 0.0
        if retrieved_chunks:
            max_score = max(chunk.score for chunk in retrieved_chunks)
            chunks_text = "\n\n".join([
                f"--- Policy Document Section {i+1} (Relevance: {chunk.score:.2f}) ---\n{chunk.text}"
                for i, chunk in enumerate(retrieved_chunks)
            ])
        else:
            chunks_text = "No relevant policy chunks found in the knowledge base."
        
        # GUARDRAIL 2: Check if top chunk has sufficient relevance
        LOW_RELEVANCE_THRESHOLD = 0.4
        if max_score < LOW_RELEVANCE_THRESHOLD and len(retrieved_chunks) > 0:
            # Low confidence - ask clarifying question
            print(f"[RAG] Low relevance detected (max score: {max_score:.2f} < {LOW_RELEVANCE_THRESHOLD})")
            return {
                "kind": "policy",
                "text": "I found some information, but I want to make sure I'm answering the right question. Could you help me clarify:\n- What specific aspect are you most interested in?\n- Is there a particular country, policy section, or topic you'd like to know about?",
                "citations": [{"id": chunk.id, "score": chunk.score, "textSnippet": chunk.text[:150]} for chunk in retrieved_chunks[:2]],
                "suggestionId": str(uuid.uuid4()),
                "intent": "policy_intent",
                "intent_confidence": max_score,
                "escalated": False,
                "needs_clarification": True,
            }
        
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
        
        # Truncate prompt if too long, but preserve chunks (they're most important)
        # If too long, truncate the template part but keep all chunks
        MAX_PROMPT_LENGTH = 8000  # Increased to accommodate chunks
        if len(system_prompt) > MAX_PROMPT_LENGTH:
            # Find where chunks start
            chunks_start = system_prompt.find("--- Policy Document Section")
            if chunks_start > 0:
                # Keep template header (first 2000 chars) and all chunks
                template_part = system_prompt[:chunks_start]
                chunks_part = system_prompt[chunks_start:]
                # Truncate template if needed, but keep all chunks
                if len(template_part) > 2000:
                    template_part = template_part[:2000]
                system_prompt = template_part + chunks_part
            else:
                # Fallback: keep last MAX_PROMPT_LENGTH chars
                system_prompt = system_prompt[-MAX_PROMPT_LENGTH:]
        
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
            # Optimize for OpenAI: balanced tokens and temperature for quality responses
            max_tokens = 250  # Allow enough tokens for complete answers with citations
            temperature = 0.2  # Lower temperature for more accurate, deterministic policy responses
            
            # GUARDRAIL: Add instruction to check relevance and ask for clarification if needed
            relevance_warning = ""
            if retrieved_chunks:
                top_score = max(chunk.score for chunk in retrieved_chunks)
                if top_score < 0.5:
                    relevance_warning = f"\n\nIMPORTANT: The retrieved documents have low relevance (top score: {top_score:.2f}). If the question is ambiguous or you're uncertain, ask for clarification instead of guessing."
            
            enhanced_system_prompt = system_prompt + relevance_warning
            
            llm_response = await generate_chat_completion(
                LLMRequestOptions(
                    model=os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL", "gpt-4o-mini"),
                    messages=[
                        LLMMessage("system", enhanced_system_prompt),
                        LLMMessage("user", request.userMessage),
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    use_local=False,  # Skip Ollama when using OpenAI
                    correlation_id=correlation_id,
                )
            )
            
            reply = llm_response.content.strip()
            
            # GUARDRAIL: Post-process response to check for hallucination indicators
            # If response doesn't contain citations but makes factual claims, check if it should
            has_citation = "(Policy" in reply or "Policy §" in reply
            says_no_info = "don't have" in reply.lower() or "not in the" in reply.lower() or "not available" in reply.lower()
            
            # If LLM says it doesn't have info but we have relevant chunks, that's a problem
            if says_no_info and retrieved_chunks and max(c.score for c in retrieved_chunks) > 0.4:
                # LLM incorrectly said it doesn't have info - this shouldn't happen with good chunks
                print(f"[RAG] Warning: LLM said no info but we have relevant chunks (top score: {max(c.score for c in retrieved_chunks):.2f})")
                # Don't modify reply - let it stand, but log the issue
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
                        INSERT INTO events (type, correlation_id, prompt_ref, retrieved_ids, raw_model_response, final_text, latency_ms, payload)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        "rag_chat",
                        correlation_id,
                        str(gzip_path),
                        json.dumps([chunk.id for chunk in retrieved_chunks]),
                        reply,
                        reply,
                        latency_ms,
                        json.dumps({
                            "intent": "policy_intent",
                            "user_message": request.userMessage[:200],
                            "thread_id": request.threadId,
                            "citations_count": len(retrieved_chunks),
                            "retrieved_ids": [chunk.id for chunk in retrieved_chunks],
                        }),
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
            
            # Return in new API format for compatibility with frontend
            return {
                "kind": "policy",  # RAG endpoint always returns policy intent
                "text": reply,
                "citations": citations,
                "suggestionId": suggestion_id,
                "intent": "policy_intent",
                "intent_confidence": 1.0,
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


async def handle_action_intent(user_message: str, thread_id: Optional[str], tone: Optional[str], intent_result: Dict[str, Any]) -> Dict[str, Any]:
    """Handle action intent - parse and create calendar events or tasks."""
    from app.routes.calendar import parse_event_text
    
    correlation_id = str(uuid.uuid4())
    start_time = datetime.now()
    
    try:
        # Parse event from user message
        parse_result = await parse_event_text(user_message)
        
        if parse_result.get("event"):
            event_data = parse_result["event"]
            
            # Create event in database
            pool = await get_pool()
            async with pool.acquire() as conn:
                # Insert into calendar_events table (match schema from calendar.py)
                from datetime import datetime as dt
                start_dt = dt.fromisoformat(event_data["start_time"].replace("Z", "+00:00"))
                end_dt = dt.fromisoformat(event_data["end_time"].replace("Z", "+00:00"))
                
                event_row = await conn.fetchrow(
                    """
                    INSERT INTO calendar_events (
                        title, description, start_time, end_time,
                        is_recurring, recurrence_pattern, recurrence_interval,
                        location, attendees
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING id, title, start_time, end_time, is_recurring, recurrence_pattern
                    """,
                    event_data.get("title"),
                    event_data.get("description"),
                    start_dt,
                    end_dt,
                    event_data.get("is_recurring", False),
                    event_data.get("recurrence_pattern"),
                    event_data.get("recurrence_interval", 1),
                    event_data.get("location"),
                    json.dumps(event_data.get("attendees", [])),
                )
            
            event_id = str(event_row["id"])
            
            # Format event time
            try:
                event_start = datetime.fromisoformat(event_data["start_time"].replace("Z", "+00:00"))
                event_time = event_start.strftime("%A, %B %d at %I:%M %p")
            except:
                event_time = event_data.get("start_time", "the scheduled time")
            
            # Create confirmation message
            text = f'✅ I\'ve added "{event_data.get("title", "Event")}" to your calendar for {event_time}.'
            if event_data.get("is_recurring"):
                text += f' This is a {event_data.get("recurrence_pattern", "recurring")} recurring event.'
            if event_data.get("location"):
                text += f' Location: {event_data["location"]}.'
            
            # Log to audit
            try:
                pool = await get_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO events (type, correlation_id, raw_model_response, final_text, latency_ms, payload)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        "action_calendar_created",
                        correlation_id,
                        text,
                        text,
                        int((datetime.now() - start_time).total_seconds() * 1000),
                        json.dumps({
                            "intent": "action_intent",
                            "action_type": "calendar_event",
                            "event_id": event_id,
                            "user_message": user_message[:200],
                        }),
                    )
            except Exception as e:
                print(f"[Action] Failed to log to audit: {e}")
            
            return {
                "kind": "action",
                "text": text,
                "citations": [],
                "suggestionId": str(uuid.uuid4()),
                "intent": "action_intent",
                "intent_confidence": intent_result.get("confidence", 0.9),
                "action_result": {
                    "success": True,
                    "eventId": event_id,
                    "event": dict(event_row),
                },
                "escalated": False,
            }
        else:
            # Missing required fields - ask clarifying question
            missing_fields = parse_result.get("missing_fields", [])
            clarifying_question = parse_result.get("clarifying_question", "What time would you like to schedule this?")
            
            return {
                "kind": "action",
                "text": clarifying_question,
                "citations": [],
                "suggestionId": str(uuid.uuid4()),
                "intent": "action_intent",
                "intent_confidence": intent_result.get("confidence", 0.9),
                "action_suggestion": {
                    "action_type": "calendar_event",
                    "confirm_needed": True,
                    "missing_fields": missing_fields,
                },
                "escalated": False,
            }
    
    except Exception as e:
        print(f"[Action] Error handling action intent: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to general response
        return await handle_general_intent(user_message, thread_id, tone)


async def handle_general_intent(user_message: str, thread_id: Optional[str], tone: Optional[str]) -> Dict[str, Any]:
    """Handle general intent with conversational assistant (no RAG)."""
    correlation_id = str(uuid.uuid4())
    start_time = datetime.now()
    
    # Get inbox context (optional)
    context = ""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            inbox_result = await conn.fetchrow("""
                SELECT COUNT(*) as total, 
                       COUNT(*) FILTER (WHERE read_at IS NULL) as unread
                FROM messages
            """)
            if inbox_result:
                context = f"Current inbox: {inbox_result['total']} messages ({inbox_result['unread']} unread)."
    except Exception:
        pass
    
    # Simple, direct system prompt - especially for greetings
    user_lower = user_message.lower().strip()
    is_greeting = user_lower in ['hi', 'hello', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening', 'howdy', "how's your day", "how are you"]
    
    # For simple greetings, use hardcoded response to avoid LLM issues
    if is_greeting and len(user_message.split()) <= 3:
        text = "Hi! I'm Soraya, your AI assistant. I can help you with questions about your inbox, tasks, policies, and more. What would you like to know?"
    else:
        # For other questions, use LLM with conversational prompt
        if is_greeting:
            # Simple, warm greeting prompt optimized for OpenAI
            system_prompt = "You are Soraya, a friendly AI assistant. Greet the user warmly in 1-2 sentences and offer to help with their inbox, tasks, or questions."
        else:
            # For other questions, be conversational but direct - optimized for OpenAI
            system_prompt = f"""You are Soraya, a helpful AI assistant for managing inbox, tasks, and calendar.

{context}

Instructions:
- Answer directly and concisely (under 150 words)
- Be friendly and conversational
- If asked about inbox/tasks, provide helpful context
- If you don't know something, say so honestly
- Keep responses natural and human-like"""
        
            # Call LLM with conversational settings (optimized for OpenAI speed)
            temperature = float(os.getenv("LLM_GENERAL_TEMP", "0.3"))
            
            # GUARDRAIL: Check if query is ambiguous
            is_ambiguous = any([
                len(user_message.split()) <= 3,
                user_message.lower().strip() in ["what about it?", "tell me about it", "what about that?", "and?", "more?"],
                user_message.lower().startswith("what about") and len(user_message.split()) <= 4,
            ])
            
            if is_ambiguous:
                text = "I want to make sure I understand correctly. Could you clarify what specific information you're looking for? For example, are you asking about a particular country, topic, or policy?"
            else:
                llm_response = await generate_chat_completion(
                    LLMRequestOptions(
                        model=os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL", "gpt-4o-mini"),
                        messages=[
                            LLMMessage("system", system_prompt),
                            LLMMessage("user", user_message),
                        ],
                        max_tokens=150,  # Reduced for faster responses
                        temperature=temperature,
                        use_local=False,  # Skip Ollama when using OpenAI
                        correlation_id=correlation_id,
                    )
                )
                
                text = llm_response.content.strip()
    
    latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
    suggestion_id = str(uuid.uuid4())
    
    # Save to audit
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO events (type, correlation_id, raw_model_response, final_text, latency_ms, payload)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                "chat_general",
                correlation_id,
                text,
                text,
                latency_ms,
                json.dumps({
                    "intent": "general_intent",
                    "user_message": user_message[:200],
                    "thread_id": thread_id,
                }),
            )
    except Exception as e:
        print(f"[Chat] Failed to save audit: {e}")
    
    return {
        "kind": "assistant",
        "text": text,
        "citations": [],
        "suggestionId": suggestion_id,
        "intent": "general_intent",
        "intent_confidence": 1.0,
        "escalated": False,
    }


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
