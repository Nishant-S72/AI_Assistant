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
from pathlib import Path
import os
import uuid
import json
import gzip
from datetime import datetime

router = APIRouter()


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

        # If using new API format (userMessage), use intent-based routing
        if request.userMessage:
            # CRITICAL: Check policy escalation BEFORE intent classification
            # This ensures sensitive content is escalated even if it matches policy/action patterns
            policy_check = check_policy(request.userMessage)
            if policy_check["action"] == "ESCALATE":
                # Escalate immediately - do not process further
                correlation_id = str(uuid.uuid4())
                escalation_reasons = [r["reason"] for r in policy_check.get("reasons", [])]
                
                # Log escalation to audit
                try:
                    pool = await get_pool()
                    async with pool.acquire() as conn:
                        await conn.execute(
                            """
                            INSERT INTO events (type, correlation_id, raw_model_response, final_text, latency_ms, payload)
                            VALUES ($1, $2, $3, $4, $5, $6)
                            """,
                            "chat_escalated",
                            correlation_id,
                            "ESCALATED",
                            "This request requires human review due to sensitive content.",
                            0,
                            json.dumps({
                                "user_message": request.userMessage[:200],
                                "escalation_reasons": escalation_reasons,
                                "escalated": True,
                            }),
                        )
                except Exception as e:
                    print(f"[Chat] Failed to log escalation: {e}")
                
                return {
                    "kind": "policy",
                    "text": f"This request requires human review due to sensitive content. I'm escalating this to a human reviewer. Reason: {', '.join(escalation_reasons[:2])}",
                    "citations": [],
                    "suggestionId": None,
                    "intent": "policy_intent",  # Default intent for escalated messages
                    "intent_confidence": 1.0,
                    "escalated": True,
                    "reasons": escalation_reasons
                }
            
            # Classify intent (after escalation check passes)
            intent_result = await classify_intent_async(request.userMessage)
            intent = intent_result["intent"]
            confidence = intent_result.get("confidence", 0.7)
            intent_method = intent_result.get("method", "rules")
            intent_reasons = intent_result.get("reasons", [])
            
            print(f"[Chat] Intent: {intent} (confidence: {confidence:.2f}, method: {intent_method})")
            
            # Check if confidence is below threshold (needs manual labeling)
            needs_manual_label = confidence < INTENT_RULES_CONFIDENCE_THRESHOLD
            
            # Route based on intent
            if intent == "policy_intent":
                # Use RAG endpoint for policy questions
                rag_request = RAGChatRequest(
                    threadId=request.threadId,
                    userMessage=request.userMessage,
                    tone=request.tone,
                    rag=True,
                )
                response = await rag_chat(rag_request)
                # Add needs_manual_label if applicable
                if needs_manual_label:
                    response["needs_manual_label"] = True
                return response
            elif intent == "action_intent":
                # Route to action handler
                return await handle_action_intent(request.userMessage, request.threadId, request.tone, intent_result)
            else:
                # general_intent - use conversational assistant
                response = await handle_general_intent(request.userMessage, request.threadId, request.tone)
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
        
        # Note: Policy escalation is now checked in main /api/chat route BEFORE routing here
        # This RAG endpoint assumes escalation has already been handled
        
        # Retrieve policy chunks if RAG enabled
        retrieved_chunks: List[VectorQueryResult] = []
        rag_error = None
        
        if request.rag:
            try:
                retrieved_chunks = await query_vectorstore(request.userMessage, k=3)
                
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
                # Insert into calendar_events table
                event_row = await conn.fetchrow(
                    """
                    INSERT INTO calendar_events (
                        title, description, start_time, end_time,
                        is_recurring, recurrence_pattern, recurrence_interval,
                        location, attendees, source, created_by
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    RETURNING id, title, start_time, end_time, is_recurring, recurrence_pattern
                    """,
                    event_data.get("title"),
                    event_data.get("description"),
                    event_data.get("start_time"),
                    event_data.get("end_time"),
                    event_data.get("is_recurring", False),
                    event_data.get("recurrence_pattern"),
                    event_data.get("recurrence_interval", 1),
                    event_data.get("location"),
                    json.dumps(event_data.get("attendees", [])),
                    "simulated",
                    "chat_assistant",
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
            # Very simple, direct prompt for greetings
            system_prompt = "You are Soraya. The user greeted you. Greet them back warmly in 1-2 sentences. Just say hello and offer help."
        else:
            # For other questions, be conversational but direct
            system_prompt = f"""You are Soraya, a helpful AI assistant.

{context}

Answer the user's question directly and helpfully. Keep it under 200 words. Be conversational and friendly."""
        
        # Call LLM with conversational settings
        temperature = float(os.getenv("LLM_GENERAL_TEMP", "0.3"))
        llm_response = await generate_chat_completion(
            LLMRequestOptions(
                model=os.getenv("LLM_MODEL", "tinyllama"),
                messages=[
                    LLMMessage("system", system_prompt),
                    LLMMessage("user", user_message),
                ],
                max_tokens=200,
                temperature=temperature,
                use_local=os.getenv("USE_OLLAMA") != "false",
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
