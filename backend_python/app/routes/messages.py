"""Message routes with thread normalization and contact deduplication."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from app.db.connection import get_pool
from app.clients.llm import generate_chat_completion, LLMMessage, LLMRequestOptions
from app.clients.vectorstore import query_vectorstore
from app.policy.policy_engine import check_policy
from app.utils.deduplication import normalize_thread_id
from app.core.logger import logger
import uuid
import os
import json

router = APIRouter()


@router.get("")
async def list_messages(folder: str = Query("all", alias="folder")):
    """List messages with optional folder filtering. Limited to 50 quality messages representing all categories."""
    try:
        pool = await get_pool()
        
        # Check database availability
        try:
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
        except Exception:
            # Database not available
            return []

        # Base query - get one representative message per thread
        base_query = """
            WITH ranked_messages AS (
                SELECT 
                    m.id,
                    m.thread_id,
                    m.sender,
                    m.body,
                    m.channel,
                    m.created_at,
                    m.contact_id,
                    c.name as contact_name,
                    c.company as contact_company,
                    c.email as contact_email,
                    c.tags as contact_tags,
                    (SELECT COUNT(*) FROM messages m2 WHERE m2.thread_id = m.thread_id) as message_count,
                    ROW_NUMBER() OVER (PARTITION BY m.thread_id ORDER BY m.created_at DESC) as rn
                FROM messages m
                JOIN contacts c ON m.contact_id = c.id
        """

        # Folder filtering
        where_clause = ""
        if folder == "leads":
            where_clause = " WHERE c.tags::text LIKE '%lead%' OR c.tags::text LIKE '%new-lead%' OR c.tags::text LIKE '%potential-interest%'"
        elif folder == "tasks":
            where_clause = """ WHERE EXISTS (
                SELECT 1 FROM tasks t WHERE t.contact_id = c.id AND t.status = 'pending'
            )"""

        query = base_query + where_clause + """
            )
            SELECT * FROM ranked_messages WHERE rn = 1
        """

        # Get messages representing all categories
        try:
            async with pool.acquire() as conn:
                all_rows = await conn.fetch(query)
                
                # Categorize messages by tags
                categorized = {
                    'urgent': [],
                    'leads': [],
                    'complaints': [],
                    'general': []
                }
                
                for row in all_rows:
                    tags = row.get('contact_tags', [])
                    if isinstance(tags, str):
                        try:
                            tags = json.loads(tags)
                        except:
                            tags = []
                    if not isinstance(tags, list):
                        tags = []
                    
                    tags_str = ' '.join(tags).lower()
                    
                    if 'urgent' in tags_str or 'escalation' in tags_str:
                        categorized['urgent'].append(dict(row))
                    elif 'lead' in tags_str or 'potential-interest' in tags_str:
                        categorized['leads'].append(dict(row))
                    elif 'complaint' in tags_str or 'refund' in tags_str:
                        categorized['complaints'].append(dict(row))
                    else:
                        categorized['general'].append(dict(row))
                
                # Select up to 50 messages, ensuring representation from all categories
                result = []
                max_per_category = 15  # Distribute across categories
                
                for category, messages in categorized.items():
                    result.extend(messages[:max_per_category])
                    if len(result) >= 50:
                        break
                
                # Sort by created_at DESC and limit to 50
                result = sorted(result, key=lambda x: x.get('created_at', ''), reverse=True)[:50]
                
        except Exception as query_error:
            print(f"Database query failed: {query_error}")
            import traceback
            traceback.print_exc()
            return []

        # If no results and in offline mode, try to load dummy inbox
        if not result and os.getenv("USE_DUMMY_INBOX") == "true":
            try:
                from app.utils.load_dummy_inbox import load_dummy_inbox
                await load_dummy_inbox()
                # Retry query
                async with pool.acquire() as conn:
                    rows = await conn.fetch(query)
                    result = [dict(row) for row in rows][:50]
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
            # Get the specific message first
            message_query = """
                SELECT 
                    m.id,
                    m.thread_id,
                    m.sender,
                    m.body,
                    m.channel,
                    m.created_at,
                    m.contact_id,
                    c.id as contact_id_full,
                    c.name as contact_name,
                    c.email as contact_email,
                    c.company as contact_company,
                    c.tags as contact_tags,
                    c.tone_pref as contact_tone_pref
                FROM messages m
                LEFT JOIN contacts c ON m.contact_id = c.id
                WHERE m.id = $1
            """
            message_row = await conn.fetchrow(message_query, message_id)
            
            if not message_row:
                raise HTTPException(status_code=404, detail="Message not found")
            
            message_data = dict(message_row)
            
            # Get thread messages
            thread_id = message_data.get("thread_id")
            if not thread_id:
                raise HTTPException(status_code=404, detail="Thread not found")
            
            thread_query = """
                SELECT 
                    m.id,
                    m.sender,
                    m.body,
                    m.created_at
                FROM messages m
                WHERE m.thread_id = $1
                ORDER BY m.created_at ASC
            """
            thread_messages = await conn.fetch(thread_query, thread_id)
            
            # Get contact information (from first message or contact table)
            contact = None
            if message_data.get("contact_id"):
                contact_query = """
                    SELECT 
                        id,
                        name,
                        email,
                        company,
                        tags,
                        tone_pref
                    FROM contacts
                    WHERE id = $1
                """
                contact_row = await conn.fetchrow(contact_query, message_data["contact_id"])
                if contact_row:
                    # Handle tags - ensure it's always an array
                    tags = contact_row.get("tags")
                    if tags is None:
                        tags = []
                    elif isinstance(tags, str):
                        # If it's a JSON string, parse it
                        try:
                            import json
                            tags = json.loads(tags)
                        except (json.JSONDecodeError, TypeError):
                            tags = []
                    elif not isinstance(tags, list):
                        # If it's not a list, make it one
                        tags = []
                    
                    contact = {
                        "id": str(contact_row["id"]),
                        "name": contact_row.get("name") or "Unknown Contact",
                        "email": contact_row.get("email"),
                        "company": contact_row.get("company"),
                        "tags": tags if isinstance(tags, list) else [],
                        "tone_pref": contact_row.get("tone_pref"),
                    }
            
            # If no contact found, create a default one from message data
            if not contact:
                # Handle tags from message data - ensure it's always an array
                tags = message_data.get("contact_tags")
                if tags is None:
                    tags = []
                elif isinstance(tags, str):
                    # If it's a JSON string, parse it
                    try:
                        import json
                        tags = json.loads(tags)
                    except (json.JSONDecodeError, TypeError):
                        tags = []
                elif not isinstance(tags, list):
                    # If it's not a list, make it one
                    tags = []
                
                contact = {
                    "id": str(message_data.get("contact_id")) or "unknown",
                    "name": message_data.get("contact_name") or "Unknown Contact",
                    "email": message_data.get("contact_email"),
                    "company": message_data.get("contact_company"),
                    "tags": tags if isinstance(tags, list) else [],
                    "tone_pref": message_data.get("contact_tone_pref"),
                }

            # Don't auto-load suggestions - user must explicitly generate them
            # This prevents default suggestions from appearing when opening threads
            # Users must click "Generate" button to create a suggestion
            suggestion = None

            # Format thread messages
            thread = [
                {
                    "id": str(msg["id"]),
                    "sender": msg["sender"],
                    "body": msg["body"],
                    "created_at": msg["created_at"].isoformat() if msg.get("created_at") else None,
                }
                for msg in thread_messages
            ]

            # Format main message
            message = {
                "id": str(message_data["id"]),
                "thread_id": str(message_data["thread_id"]),
                "sender": message_data["sender"],
                "body": message_data["body"],
                "channel": message_data.get("channel"),
                "created_at": message_data["created_at"].isoformat() if message_data.get("created_at") else None,
            }

            result = {
                "message": message,
                "thread": thread,
                "suggestion": suggestion,
                "contact": contact,
            }
            return result
    except HTTPException:
        raise
    except Exception as error:
        print(f"Error fetching thread: {error}")
        import traceback
        traceback.print_exc()
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

            # Retrieve relevant policy documents using RAG
            # Combine the latest message and conversation context for better retrieval
            query_text = latest_customer_message
            if len(customer_messages) > 1:
                # Include context from recent messages
                recent_context = " ".join([m["body"] for m in customer_messages[-3:]])
                query_text = f"{recent_context} {latest_customer_message}"
            
            print(f"[Suggestion] Querying vector store with: {query_text[:100]}...")
            retrieved_chunks = await query_vectorstore(query_text, k=3)
            print(f"[Suggestion] Retrieved {len(retrieved_chunks)} chunks from vector store")
            
            # Filter chunks by relevance (similarity threshold)
            SIMILARITY_THRESHOLD = 0.3
            filtered_chunks = [chunk for chunk in retrieved_chunks if chunk.score >= SIMILARITY_THRESHOLD]
            print(f"[Suggestion] {len(filtered_chunks)} chunks passed similarity threshold (>{SIMILARITY_THRESHOLD})")
            
            # Build policy context if we have relevant chunks
            policy_context = ""
            if filtered_chunks:
                policy_context = "\n\nRelevant Policy/Knowledge Base Information:\n"
                for i, chunk in enumerate(filtered_chunks, 1):
                    policy_context += f"{i}. {chunk.text[:300]}...\n"
                    if chunk.metadata.get("section"):
                        policy_context += f"   (Source: {chunk.metadata.get('section', 'Policy Document')})\n"
                policy_context += "\nIMPORTANT: Use the above policy/knowledge base information to inform your response. Reference specific policies when relevant, but keep the tone natural and conversational.\n"
                print(f"[Suggestion] Added {len(filtered_chunks)} policy chunks to context")
            else:
                print(f"[Suggestion] No relevant policy chunks found (all below threshold or empty)")

            # Get user's name and email for signature
            user_name = os.getenv("USER_NAME", "Soraya")
            user_email = os.getenv("USER_EMAIL", "soraya@example.com")
            
            # Build prompt
            system_prompt = f"""You're helping write a reply to a customer. Talk to them like a real person, not a robot.

Tone: {preferred_tone}
You are replying to: {contact_name}{f' from {contact_company}' if contact_company else ''}

What they've been saying:
{chr(10).join([f"[{m['sender']}]: {m['body']}" for m in thread_messages])}
{policy_context}
CRITICAL SIGNATURE RULES:
- You MUST sign the email with YOUR name: {user_name}
- You MUST include YOUR email: {user_email}
- DO NOT use the recipient's name ({contact_name}) or company ({contact_company or 'N/A'}) in the signature
- The signature format should be: "Best,\n{user_name}\n{user_email}"

Write a natural, {preferred_tone} reply. No templates, no corporate speak - just respond like you're actually talking to them. Address what they need, be helpful, and keep it real. Keep it under 250 words. Be concise and direct. Always end with the correct signature using {user_name} and {user_email}."""

            user_prompt = f"Latest message from them:\n{latest_customer_message}\n\nWrite a natural, {preferred_tone} reply. Remember: sign with YOUR name ({user_name}) and email ({user_email}), NOT the recipient's name ({contact_name})."

            # Generate suggestion - prioritize OPENAI_MODEL explicitly
            openai_model = os.getenv("OPENAI_MODEL")
            if not openai_model:
                openai_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
                print(f"[Suggestion] ⚠️ OPENAI_MODEL not set, using LLM_MODEL: {openai_model}")
            else:
                print(f"[Suggestion] ✅ Using OPENAI_MODEL: {openai_model}")
            
            llm_response = await generate_chat_completion(
                LLMRequestOptions(
                    model=openai_model,
                    messages=[
                        LLMMessage("system", system_prompt),
                        LLMMessage("user", user_prompt),
                    ],
                    temperature=0.5,
                    max_tokens=150,
                    use_local=False,  # Skip Ollama when using OpenAI
                    correlation_id=correlation_id or str(uuid.uuid4()),
                )
            )
            
            print(f"[Suggestion] Generated response using adapter: {getattr(llm_response, 'adapter', 'unknown')}, model: {getattr(llm_response, 'model', 'unknown')}")

            suggestion_text = llm_response.content.strip()

            # Check policy
            policy_result = check_policy(suggestion_text)

            # Store suggestion
            suggestion_id = str(uuid.uuid4())
            # Create a prompt snapshot for storage
            prompt_snapshot = f"System: {system_prompt}\n\nUser: {user_prompt}"
            
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO suggestions (id, message_id, prompt, model_response, final_text, edited, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, NOW())
                    """,
                    suggestion_id,
                    message_id,
                    prompt_snapshot,
                    suggestion_text,
                    suggestion_text,
                    False,
                )

            # Trigger tag update in background after generating suggestion
            # This ensures tags reflect the latest conversation
            try:
                from app.services.contact_tags import update_contact_tags
                import asyncio
                # Get contact_id from the message
                contact_id_row = await conn.fetchrow(
                    "SELECT contact_id FROM messages WHERE id = $1",
                    message_id
                )
                if contact_id_row:
                    contact_id = contact_id_row["contact_id"]
                    # Update tags in background (don't wait)
                    asyncio.create_task(update_contact_tags(contact_id, pool))
            except Exception as e:
                print(f"[Suggestion] Failed to trigger tag update: {e}")
            
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

