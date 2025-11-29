"""Message routes."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from app.db.connection import get_pool
from app.clients.llm import generate_chat_completion, LLMMessage, LLMRequestOptions
from app.policy.policy_engine import check_policy
import uuid
import os

router = APIRouter()


@router.get("")
async def list_messages(folder: str = Query("all", alias="folder")):
    """List messages with optional folder filtering."""
    try:
        pool = await get_pool()
        
        # Check database availability
        try:
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
        except Exception:
            # Database not available
            return []

        query = """
            SELECT 
                m.id,
                m.thread_id,
                m.sender,
                m.body,
                m.channel,
                m.created_at,
                c.name as contact_name,
                c.company as contact_company,
                c.email as contact_email,
                (SELECT COUNT(*) FROM messages m2 WHERE m2.thread_id = m.thread_id) as message_count
            FROM messages m
            JOIN contacts c ON m.contact_id = c.id
        """

        # Folder filtering
        if folder == "leads":
            query += " WHERE c.tags::text LIKE '%lead%'"
        elif folder == "tasks":
            query += """ WHERE EXISTS (
                SELECT 1 FROM tasks t WHERE t.contact_id = c.id AND t.status = 'pending'
            )"""

        query += " ORDER BY m.created_at DESC"

        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(query)
                result = [dict(row) for row in rows]
        except Exception as query_error:
            print(f"Database query failed: {query_error}")
            return []

        # If no results and in offline mode, try to load dummy inbox
        if not result and os.getenv("USE_DUMMY_INBOX") == "true":
            try:
                from app.utils.load_dummy_inbox import load_dummy_inbox
                await load_dummy_inbox()
                # Retry query
                async with pool.acquire() as conn:
                    rows = await conn.fetch(query)
                    result = [dict(row) for row in rows]
            except Exception as load_error:
                print(f"Could not load dummy inbox: {load_error}")

        return result
    except Exception as error:
        print(f"Error fetching messages: {error}")
        error_msg = str(error)
        if "connect" in error_msg.lower() or "connection" in error_msg.lower():
            return []
        raise HTTPException(status_code=500, detail=f"Failed to fetch messages: {error_msg}")


@router.get("/{message_id}")
async def get_thread(message_id: str):
    """Get thread with contact and latest suggestion."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Get thread messages
            thread_query = """
                SELECT 
                    m.id,
                    m.sender,
                    m.body,
                    m.created_at,
                    c.name as contact_name,
                    c.email as contact_email,
                    c.company as contact_company,
                    c.tags as contact_tags,
                    c.tone_pref as contact_tone_pref
                FROM messages m
                JOIN contacts c ON m.contact_id = c.id
                WHERE m.thread_id = (SELECT thread_id FROM messages WHERE id = $1)
                ORDER BY m.created_at ASC
            """
            messages = await conn.fetch(thread_query, message_id)
            
            if not messages:
                raise HTTPException(status_code=404, detail="Thread not found")

            # Get latest suggestion if available
            suggestion_query = """
                SELECT * FROM suggestions
                WHERE message_id = $1
                ORDER BY created_at DESC
                LIMIT 1
            """
            suggestion = await conn.fetchrow(suggestion_query, message_id)

            result = {
                "messages": [dict(msg) for msg in messages],
                "suggestion": dict(suggestion) if suggestion else None,
            }
            return result
    except HTTPException:
        raise
    except Exception as error:
        print(f"Error fetching thread: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch thread: {str(error)}")


@router.post("/{message_id}/generate")
async def generate_suggestion(
    message_id: str,
    tone: Optional[str] = "warm",
    correlation_id: Optional[str] = None,
):
    """Generate AI suggestion for a message."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Get thread messages
            thread_query = """
                SELECT 
                    m.sender,
                    m.body,
                    m.created_at,
                    c.name as contact_name,
                    c.company as contact_company,
                    c.tone_pref as contact_tone_pref
                FROM messages m
                JOIN contacts c ON m.contact_id = c.id
                WHERE m.thread_id = (SELECT thread_id FROM messages WHERE id = $1)
                ORDER BY m.created_at ASC
            """
            messages = await conn.fetch(thread_query, message_id)
            
            if not messages:
                raise HTTPException(status_code=404, detail="Message not found")

            contact = dict(messages[0])
            contact_name = contact.get("contact_name", "Customer")
            contact_company = contact.get("contact_company")
            preferred_tone = contact.get("contact_tone_pref") or tone

            # Build thread summary
            thread_messages = [dict(msg) for msg in messages]
            customer_messages = [m for m in thread_messages if m["sender"] == "contact"]
            latest_customer_message = customer_messages[-1]["body"] if customer_messages else ""

            # Build prompt
            system_prompt = f"""You're helping write a reply to a customer. Talk to them like a real person, not a robot.

Tone: {preferred_tone}
Contact: {contact_name}{f' from {contact_company}' if contact_company else ''}

What they've been saying:
{chr(10).join([f"[{m['sender']}]: {m['body']}" for m in thread_messages])}

Write a natural, {preferred_tone} reply. No templates, no corporate speak - just respond like you're actually talking to them. Address what they need, be helpful, and keep it real. Keep it under 250 words. Be concise and direct."""

            user_prompt = f"Latest message from them:\n{latest_customer_message}\n\nWrite a natural, {preferred_tone} reply."

            # Generate suggestion
            llm_response = await generate_chat_completion(
                LLMRequestOptions(
                    model=os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or "tinyllama",
                    messages=[
                        LLMMessage("system", system_prompt),
                        LLMMessage("user", user_prompt),
                    ],
                    temperature=0.5,
                    max_tokens=150,
                    use_local=os.getenv("USE_OLLAMA") != "false",
                    correlation_id=correlation_id or str(uuid.uuid4()),
                )
            )

            suggestion_text = llm_response.content.strip()

            # Check policy
            policy_result = check_policy(suggestion_text)

            # Store suggestion
            suggestion_id = str(uuid.uuid4())
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO suggestions (id, message_id, model_response, final_text, edited, created_at)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                    """,
                    suggestion_id,
                    message_id,
                    suggestion_text,
                    suggestion_text,
                    False,
                )

            return {
                "id": suggestion_id,
                "message_id": message_id,
                "suggestion": suggestion_text,
                "policy_check": {
                    "action": policy_result["action"],
                    "reasons": policy_result.get("reasons", []),
                },
                "model": getattr(llm_response, "model", "unknown"),
                "correlation_id": getattr(llm_response, "correlation_id", None),
            }
    except HTTPException:
        raise
    except Exception as error:
        print(f"Error generating suggestion: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to generate suggestion: {str(error)}")

