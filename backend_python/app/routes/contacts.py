"""Contact routes with deduplication support."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from app.db.connection import get_pool
from app.clients.llm import generate_chat_completion, LLMMessage, LLMRequestOptions
from app.services.cache_manager import (
    get_contact_summary_cache, set_contact_summary_cache
)
from app.utils.deduplication import merge_contacts
from app.core.logger import logger
import json
import os
import uuid

router = APIRouter()


@router.get("")
async def list_contacts(
    search: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
):
    """List all contacts with optional search and tag filtering."""
    try:
        pool = await get_pool()
        query = """
            SELECT DISTINCT
                c.id,
                c.name,
                c.email,
                c.phone,
                c.company,
                c.tags,
                c.tone_pref,
                c.created_at,
                (SELECT COUNT(*) FROM messages m WHERE m.contact_id = c.id) as message_count,
                (SELECT COUNT(*) FROM tasks t WHERE t.contact_id = c.id AND t.status = 'pending') as pending_tasks,
                (SELECT MAX(created_at) FROM messages m WHERE m.contact_id = c.id) as last_message_at
            FROM contacts c
        """

        params = []
        conditions = []

        if search:
            conditions.append("(LOWER(c.name) LIKE LOWER($1) OR LOWER(c.email) LIKE LOWER($1) OR LOWER(c.company) LIKE LOWER($1))")
            params.append(f"%{search}%")

        if tag:
            # Handle JSON array format - tags are stored as JSONB arrays
            # Match both with and without quotes
            param_index = len(params) + 1
            conditions.append(f"c.tags::text LIKE ${param_index}")
            params.append(f'%"{tag}"%')  # JSON array format: ["tag"]

        if conditions:
            query += f" WHERE {' AND '.join(conditions)}"

        query += " ORDER BY last_message_at DESC NULLS LAST, c.name ASC"

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        # Parse JSONB tags and deduplicate contacts
        contacts_dict = {}  # Key by email for deduplication
        for row in rows:
            contact = dict(row)
            tags = contact.get("tags")
            if isinstance(tags, str):
                try:
                    contact["tags"] = json.loads(tags)
                except:
                    contact["tags"] = []
            elif not isinstance(tags, list):
                contact["tags"] = []
            
            # Deduplicate by email (same email → same contact)
            email = contact.get("email", "").lower().strip()
            if email:
                if email in contacts_dict:
                    # Merge with existing contact
                    contacts_dict[email] = merge_contacts(contacts_dict[email], contact)
                else:
                    contacts_dict[email] = contact
            else:
                # No email, add as-is (use ID as key)
                contacts_dict[contact.get("id", str(uuid.uuid4()))] = contact
        
        # Return deduplicated contacts as list
        contacts = list(contacts_dict.values())
        
        # Sort by last_message_at DESC
        contacts.sort(key=lambda x: x.get("last_message_at") or "", reverse=True)

        return contacts
    except Exception as error:
        print(f"Error fetching contacts: {error}")
        raise HTTPException(status_code=500, detail="Failed to fetch contacts")


@router.get("/{contact_id}")
async def get_contact(contact_id: str):
    """Get contact details."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 
                    c.*,
                    (SELECT COUNT(*) FROM messages m WHERE m.contact_id = c.id) as message_count,
                    (SELECT COUNT(*) FROM tasks t WHERE t.contact_id = c.id AND t.status = 'pending') as pending_tasks,
                    (SELECT MAX(created_at) FROM messages m WHERE m.contact_id = c.id) as last_message_at
                FROM contacts c
                WHERE c.id = $1
                """,
                contact_id,
            )

            if not row:
                raise HTTPException(status_code=404, detail="Contact not found")

            contact = dict(row)
            tags = contact.get("tags")
            if isinstance(tags, str):
                try:
                    contact["tags"] = json.loads(tags)
                except:
                    contact["tags"] = []
            elif not isinstance(tags, list):
                contact["tags"] = []

            return contact
    except HTTPException:
        raise
    except Exception as error:
        print(f"Error fetching contact: {error}")
        raise HTTPException(status_code=500, detail="Failed to fetch contact")


@router.post("/{contact_id}/update-tags")
async def update_contact_tags_endpoint(contact_id: str):
    """Update contact tags based on AI analysis of chat history."""
    try:
        from app.services.contact_tags import update_contact_tags
        tags = await update_contact_tags(contact_id)
        return {
            "success": True,
            "contact_id": contact_id,
            "tags": tags
        }
    except Exception as error:
        print(f"Error updating contact tags: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to update tags: {str(error)}")


@router.get("/{contact_id}/messages")
async def get_contact_messages(
    contact_id: str,
    limit: int = Query(50),
    offset: int = Query(0),
):
    """Get all messages from a contact."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT 
                    m.id,
                    m.thread_id,
                    m.sender,
                    m.body,
                    m.channel,
                    m.created_at,
                    m.processed
                FROM messages m
                WHERE m.contact_id = $1
                ORDER BY m.created_at DESC
                LIMIT $2 OFFSET $3
                """,
                contact_id,
                limit,
                offset,
            )

            return [dict(row) for row in rows]
    except Exception as error:
        print(f"Error fetching contact messages: {error}")
        raise HTTPException(status_code=500, detail="Failed to fetch contact messages")


@router.get("/{contact_id}/summary")
async def get_contact_summary(contact_id: str):
    """Get LLM-generated interaction summary."""
    try:
        # Check cache first
        cached = get_contact_summary_cache(contact_id)
        if cached:
            print(f"[ContactSummary] Using cached summary for {contact_id}")
            return cached
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Get contact info
            contact_row = await conn.fetchrow(
                "SELECT name, email, company, tags, tone_pref FROM contacts WHERE id = $1",
                contact_id,
            )

            if not contact_row:
                raise HTTPException(status_code=404, detail="Contact not found")

            contact = dict(contact_row)
            tags = contact.get("tags")
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except:
                    tags = []
            elif not isinstance(tags, list):
                tags = []

            # Get ALL messages for deep analysis
            messages = await conn.fetch(
                """
                SELECT sender, body, created_at, thread_id
                FROM messages 
                WHERE contact_id = $1 
                ORDER BY created_at ASC
                """,
                contact_id,
            )
            
            # Auto-update tags if they're missing or outdated (no tags or only "new" tag)
            current_tags = tags if isinstance(tags, list) else []
            should_update_tags = (
                not current_tags or 
                current_tags == ["new"] or 
                len(current_tags) == 0
            )
            
            if should_update_tags and len(messages) > 0:
                # Update tags in background (don't wait for it)
                try:
                    from app.services.contact_tags import update_contact_tags
                    import asyncio
                    # Run tag update in background
                    asyncio.create_task(update_contact_tags(contact_id, pool))
                except Exception as e:
                    print(f"[Summary] Failed to trigger tag update: {e}")

            if not messages:
                # Still return task stats and message count even if no messages
                task_stats_row = await conn.fetchrow(
                    """
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE status = 'pending') as pending,
                        COUNT(*) FILTER (WHERE status = 'completed') as completed
                    FROM tasks
                    WHERE contact_id = $1
                    """,
                    contact_id,
                )
                task_stats = {
                    "total": int(task_stats_row["total"]) if task_stats_row else 0,
                    "pending": int(task_stats_row["pending"]) if task_stats_row else 0,
                    "completed": int(task_stats_row["completed"]) if task_stats_row else 0,
                }
                return {
                    "summary": "No interaction history available.",
                    "recommendations": [],
                    "recentConversations": [],
                    "messageCount": 0,
                    "taskStats": task_stats,
                }

            # Build email history
            email_history = []
            for msg in messages:
                email_history.append(f"[{msg['sender']}] {msg['body']}")

            # Use all email history - no limits
            simple_email_history = "\n\n".join(email_history)  # All messages

            # Generate summary using LLM
            summary_prompt = f"""You are analyzing the email history with {contact['name']}{f' from {contact["company"]}' if contact.get('company') else ''}.

Email history:
{simple_email_history}

Write a natural, insightful summary of this relationship. Focus on:
- What has happened in recent interactions
- Their perception of the company
- Recommended actions

Be conversational and humane. Do NOT use a rigid structure. Write naturally as if you're explaining this to a colleague. Keep it under 250 words."""

            # Generate recommendations
            recommendations_prompt = f"""Based on this email history with {contact['name']}:

{simple_email_history}

Provide 2-3 actionable recommendations. Be specific and practical. Keep each recommendation under 50 words."""

            # Make LLM calls in parallel for speed
            import asyncio
            
            async def generate_summary():
                try:
                    llm_response = await generate_chat_completion(
                        LLMRequestOptions(
                            model=os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL", "gpt-4o-mini"),
                            messages=[
                                LLMMessage("system", "You are a helpful assistant analyzing customer relationships."),
                                LLMMessage("user", summary_prompt),
                            ],
                            temperature=0.7,
                            max_tokens=None,  # No token limit
                        )
                    )
                    return llm_response.content.strip()
                except Exception as e:
                    import traceback
                    print(f"Summary generation error: {e}")
                    traceback.print_exc()
                    return None

            async def generate_recommendations():
                try:
                    rec_response = await generate_chat_completion(
                        LLMRequestOptions(
                            model=os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL", "gpt-4o-mini"),
                            messages=[
                                LLMMessage("system", "You are a helpful assistant providing actionable recommendations."),
                                LLMMessage("user", recommendations_prompt),
                            ],
                            temperature=0.7,
                            max_tokens=None,  # No token limit
                        )
                    )
                    rec_text = rec_response.content.strip()
                    # Parse recommendations
                    recommendations = [
                        r.strip()
                        for r in rec_text.replace("•", "\n").replace("-", "\n").split("\n")
                        if r.strip() and len(r.strip()) > 10
                    ][:3]
                    return recommendations
                except Exception as e:
                    import traceback
                    print(f"Recommendations generation error: {e}")
                    traceback.print_exc()
                    return []

            # Run LLM calls sequentially (one after the other) to avoid rate limits
            # 1. Generate summary first
            try:
                summary_text = await generate_summary()
            except Exception as e:
                import traceback
                print(f"Summary generation error: {e}")
                traceback.print_exc()
                summary_text = None
            
            # 2. Generate recommendations after summary completes
            try:
                recommendations = await generate_recommendations()
            except Exception as e:
                import traceback
                print(f"Recommendations generation error: {e}")
                traceback.print_exc()
                recommendations = []
            
            if not summary_text:
                # Fallback error handling - get task stats and return error
                error_msg = "Summary generation returned None"
                task_stats_row = await conn.fetchrow(
                    """
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE status = 'pending') as pending,
                        COUNT(*) FILTER (WHERE status = 'completed') as completed
                    FROM tasks
                    WHERE contact_id = $1
                    """,
                    contact_id,
                )
                task_stats = {
                    "total": int(task_stats_row["total"]) if task_stats_row else 0,
                    "pending": int(task_stats_row["pending"]) if task_stats_row else 0,
                    "completed": int(task_stats_row["completed"]) if task_stats_row else 0,
                }
                message_count_row = await conn.fetchrow(
                    "SELECT COUNT(*) as count FROM messages WHERE contact_id = $1",
                    contact_id
                )
                message_count = int(message_count_row["count"]) if message_count_row else 0
                
                return {
                    "summary": "Failed to generate summary. Please try again.",
                    "recommendations": recommendations if recommendations else [],
                    "recentConversations": [],
                    "messageCount": message_count,
                    "taskStats": task_stats,
                }

            # 3. Generate conversation summaries sequentially (one after the other)
            thread_ids = list(set([msg["thread_id"] for msg in messages]))[-3:]
            conversation_summaries = []

            for thread_id in thread_ids:
                thread_messages = [msg for msg in messages if msg["thread_id"] == thread_id]
                thread_text = "\n".join([f"[{m['sender']}] {m['body']}" for m in thread_messages])

                try:
                    conv_response = await generate_chat_completion(
                        LLMRequestOptions(
                            model=os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL", "gpt-4o-mini"),
                            messages=[
                                LLMMessage("system", "Summarize this conversation in 1-2 sentences."),
                                LLMMessage("user", f"Conversation:\n{thread_text}"),
                            ],
                            temperature=0.7,
                            max_tokens=None,  # No token limit
                        )
                    )
                    conversation_summaries.append(conv_response.content.strip())
                except Exception as e:
                    print(f"Conversation summary error for thread {thread_id}: {e}")
                    pass

            # Get task statistics and message count (reuse connection)
            task_stats_row = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed
                FROM tasks
                WHERE contact_id = $1
                """,
                contact_id,
            )
            
            task_stats = {
                "total": int(task_stats_row["total"]) if task_stats_row else 0,
                "pending": int(task_stats_row["pending"]) if task_stats_row else 0,
                "completed": int(task_stats_row["completed"]) if task_stats_row else 0,
            }

            message_count_row = await conn.fetchrow(
                "SELECT COUNT(*) as count FROM messages WHERE contact_id = $1",
                contact_id
            )
            message_count = int(message_count_row["count"]) if message_count_row else 0

            # Format recent conversations as objects (not just strings)
            recent_conversations = []
            for i, thread_id in enumerate(thread_ids):
                thread_messages = [msg for msg in messages if msg["thread_id"] == thread_id]
                if thread_messages:
                    recent_conversations.append({
                        "thread_id": thread_id,
                        "summary": conversation_summaries[i] if i < len(conversation_summaries) else "",
                        "message_count": len(thread_messages),
                        "last_message_at": thread_messages[-1]["created_at"].isoformat() if thread_messages else None,
                    })

            response_data = {
                "summary": summary_text,
                "recommendations": recommendations,
                "recentConversations": recent_conversations,
                "messageCount": message_count,
                "taskStats": task_stats,
            }
            
            # Cache the response
            set_contact_summary_cache(contact_id, response_data)
            
            return response_data
    except HTTPException:
        raise
    except Exception as error:
        print(f"Error generating contact summary: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(error)}")

