"""Contact routes."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from app.db.connection import get_pool
from app.clients.llm import generate_chat_completion, LLMMessage, LLMRequestOptions
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
            conditions.append("c.tags::text LIKE $2")
            params.append(f'%"{tag}"%')

        if conditions:
            query += f" WHERE {' AND '.join(conditions)}"

        query += " ORDER BY last_message_at DESC NULLS LAST, c.name ASC"

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        # Parse JSONB tags
        contacts = []
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
            contacts.append(contact)

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

            if not messages:
                return {
                    "summary": "No interaction history available.",
                    "recommendations": [],
                    "conversation_summaries": [],
                }

            # Build email history
            email_history = []
            for msg in messages:
                email_history.append(f"[{msg['sender']}] {msg['body']}")

            simple_email_history = "\n\n".join(email_history[-50:])  # Last 50 messages

            # Generate summary using LLM
            summary_prompt = f"""You are analyzing the email history with {contact['name']}{f' from {contact["company"]}' if contact.get('company') else ''}.

Email history:
{simple_email_history}

Write a natural, insightful summary of this relationship. Focus on:
- What has happened in recent interactions
- Their perception of the company
- Recommended actions

Be conversational and humane. Do NOT use a rigid structure. Write naturally as if you're explaining this to a colleague. Keep it under 250 words."""

            try:
                llm_response = await generate_chat_completion(
                    LLMRequestOptions(
                        model=os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or "tinyllama",
                        messages=[
                            LLMMessage("system", "You are a helpful assistant analyzing customer relationships."),
                            LLMMessage("user", summary_prompt),
                        ],
                        temperature=0.7,
                        max_tokens=200,
                        use_local=os.getenv("USE_OLLAMA") != "false",
                    )
                )

                summary_text = llm_response.content.strip()
            except Exception as llm_error:
                print(f"LLM error generating summary: {llm_error}")
                return {
                    "summary": f"Failed to generate summary. Please ensure Ollama is running and {os.getenv('LLM_MODEL', 'tinyllama')} model is installed.",
                    "recommendations": [],
                    "conversation_summaries": [],
                }

            # Generate recommendations
            recommendations_prompt = f"""Based on this email history with {contact['name']}:

{simple_email_history}

Provide 2-3 actionable recommendations. Be specific and practical. Keep each recommendation under 50 words."""

            try:
                rec_response = await generate_chat_completion(
                    LLMRequestOptions(
                        model=os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or "tinyllama",
                        messages=[
                            LLMMessage("system", "You are a helpful assistant providing actionable recommendations."),
                            LLMMessage("user", recommendations_prompt),
                        ],
                        temperature=0.7,
                        max_tokens=150,
                        use_local=os.getenv("USE_OLLAMA") != "false",
                    )
                )

                recommendations_text = rec_response.content.strip()
                # Parse recommendations (simple split by newlines or bullets)
                recommendations = [
                    r.strip()
                    for r in recommendations_text.replace("•", "\n").replace("-", "\n").split("\n")
                    if r.strip() and len(r.strip()) > 10
                ][:3]
            except Exception:
                recommendations = []

            # Generate conversation summaries for last 3 threads
            thread_ids = list(set([msg["thread_id"] for msg in messages]))[-3:]
            conversation_summaries = []

            for thread_id in thread_ids:
                thread_messages = [msg for msg in messages if msg["thread_id"] == thread_id]
                thread_text = "\n".join([f"[{m['sender']}] {m['body']}" for m in thread_messages])

                try:
                    conv_response = await generate_chat_completion(
                        LLMRequestOptions(
                            model=os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or "tinyllama",
                            messages=[
                                LLMMessage("system", "Summarize this conversation in 1-2 sentences."),
                                LLMMessage("user", f"Conversation:\n{thread_text}"),
                            ],
                            temperature=0.7,
                            max_tokens=80,
                            use_local=os.getenv("USE_OLLAMA") != "false",
                        )
                    )
                    conversation_summaries.append(conv_response.content.strip())
                except Exception:
                    pass

            return {
                "summary": summary_text,
                "recommendations": recommendations,
                "conversation_summaries": conversation_summaries,
            }
    except HTTPException:
        raise
    except Exception as error:
        print(f"Error generating contact summary: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(error)}")

