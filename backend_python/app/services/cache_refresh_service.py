"""Service for automatically refreshing caches when conversations change."""
from typing import Optional, List, Dict, Any
from app.db.connection import get_pool
from app.services.cache_manager import (
    get_affected_contacts,
    get_affected_threads,
    clear_affected_lists,
    set_contact_summary_cache,
    set_contact_tags_cache,
    set_summary_cache,
    set_badges_cache,
)
import asyncio
import json


async def refresh_affected_caches(
    contact_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    reason: str = "unknown"
):
    """
    Automatically refresh summaries, tags, and badges for affected contacts and threads.
    
    Args:
        contact_id: Specific contact ID to refresh (optional)
        thread_id: Specific thread ID that changed (optional)
        reason: Reason for refresh (e.g., "new_message", "new_conversation")
    """
    print(f"[CacheRefresh] Starting refresh - Reason: {reason}, Contact: {contact_id}, Thread: {thread_id}")
    
    try:
        pool = await get_pool()
        
        # Get list of affected contacts
        affected_contacts = get_affected_contacts()
        if contact_id and contact_id not in affected_contacts:
            affected_contacts.append(contact_id)
        
        # Refresh contact-specific caches
        if affected_contacts:
            print(f"[CacheRefresh] Refreshing {len(affected_contacts)} contacts")
            for cid in affected_contacts:
                try:
                    await _refresh_contact_cache(cid, pool)
                except Exception as e:
                    print(f"[CacheRefresh] Error refreshing contact {cid}: {e}")
        
        # Refresh dashboard summary and badges
        await _refresh_dashboard_cache(pool)
        
        # Clear affected lists after refresh
        clear_affected_lists()
        
        print(f"[CacheRefresh] Refresh completed successfully")
        
    except Exception as e:
        print(f"[CacheRefresh] Error during refresh: {e}")
        import traceback
        traceback.print_exc()


async def _refresh_contact_cache(contact_id: str, pool):
    """Refresh cache for a specific contact: summary, tags, and related data."""
    print(f"[CacheRefresh] Refreshing contact cache for {contact_id}")
    
    try:
        async with pool.acquire() as conn:
            # 1. Refresh tags first (they affect summaries)
            try:
                from app.services.contact_tags import update_contact_tags
                tags = await update_contact_tags(contact_id, pool)
                if tags:
                    set_contact_tags_cache(contact_id, tags)
                    print(f"[CacheRefresh] Tags refreshed for {contact_id}: {tags}")
            except Exception as e:
                print(f"[CacheRefresh] Error refreshing tags for {contact_id}: {e}")
            
            # 2. Refresh contact summary
            try:
                from app.routes.contacts import get_contact_summary
                # Call the endpoint logic directly (bypassing FastAPI)
                summary_data = await _generate_contact_summary_direct(contact_id, pool)
                if summary_data:
                    set_contact_summary_cache(contact_id, summary_data)
                    print(f"[CacheRefresh] Summary refreshed for {contact_id}")
            except Exception as e:
                print(f"[CacheRefresh] Error refreshing summary for {contact_id}: {e}")
                
    except Exception as e:
        print(f"[CacheRefresh] Error in _refresh_contact_cache for {contact_id}: {e}")


async def _generate_contact_summary_direct(contact_id: str, pool) -> Optional[Dict[str, Any]]:
    """Generate contact summary directly (bypassing FastAPI endpoint)."""
    try:
        from app.clients.llm import generate_chat_completion, LLMMessage, LLMRequestOptions
        import os
        
        async with pool.acquire() as conn:
            # Get contact info
            contact_row = await conn.fetchrow(
                "SELECT name, email, company, tags, tone_pref FROM contacts WHERE id = $1",
                contact_id,
            )
            
            if not contact_row:
                return None
            
            contact = dict(contact_row)
            tags = contact.get("tags")
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except:
                    tags = []
            elif not isinstance(tags, list):
                tags = []
            
            # Get messages
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
                # Return minimal summary
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
            
            simple_email_history = "\n\n".join(email_history)
            
            # Generate summary
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

            # Generate summary
            summary_response = await generate_chat_completion(
                LLMRequestOptions(
                    model=os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL", "gpt-4o-mini"),
                    messages=[
                        LLMMessage("system", "You are a helpful assistant analyzing customer relationships."),
                        LLMMessage("user", summary_prompt),
                    ],
                    temperature=0.7,
                    max_tokens=None,
                )
            )
            summary_text = summary_response.content.strip()
            
            # Generate recommendations
            rec_response = await generate_chat_completion(
                LLMRequestOptions(
                    model=os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL", "gpt-4o-mini"),
                    messages=[
                        LLMMessage("system", "You are a helpful assistant providing actionable recommendations."),
                        LLMMessage("user", recommendations_prompt),
                    ],
                    temperature=0.7,
                    max_tokens=None,
                )
            )
            rec_text = rec_response.content.strip()
            recommendations = [
                r.strip()
                for r in rec_text.replace("•", "\n").replace("-", "\n").split("\n")
                if r.strip() and len(r.strip()) > 10
            ][:3]
            
            # Generate conversation summaries
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
                            max_tokens=None,
                        )
                    )
                    conversation_summaries.append(conv_response.content.strip())
                except Exception as e:
                    print(f"[CacheRefresh] Conversation summary error for thread {thread_id}: {e}")
                    pass
            
            # Get task statistics
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
            
            # Format recent conversations
            recent_conversations = []
            for i, tid in enumerate(thread_ids):
                thread_messages = [msg for msg in messages if msg["thread_id"] == tid]
                if thread_messages:
                    recent_conversations.append({
                        "thread_id": tid,
                        "summary": conversation_summaries[i] if i < len(conversation_summaries) else "",
                        "message_count": len(thread_messages),
                        "last_message_at": thread_messages[-1]["created_at"].isoformat() if thread_messages else None,
                    })
            
            return {
                "summary": summary_text,
                "recommendations": recommendations,
                "recentConversations": recent_conversations,
                "messageCount": message_count,
                "taskStats": task_stats,
            }
            
    except Exception as e:
        print(f"[CacheRefresh] Error generating contact summary: {e}")
        import traceback
        traceback.print_exc()
        return None


async def _refresh_dashboard_cache(pool):
    """Refresh dashboard summary and badges."""
    print(f"[CacheRefresh] Refreshing dashboard cache")
    
    try:
        from app.routes.summary import get_summary
        from fastapi import BackgroundTasks
        
        # Generate summary in background (this will update the cache)
        # We'll call the summary generation logic directly
        await _generate_dashboard_summary_direct(pool)
        
    except Exception as e:
        print(f"[CacheRefresh] Error refreshing dashboard cache: {e}")
        import traceback
        traceback.print_exc()


async def _generate_dashboard_summary_direct(pool):
    """Generate dashboard summary directly (bypassing FastAPI endpoint)."""
    try:
        from app.routes.summary import _generate_summary_async
        from datetime import datetime
        import json
        
        async with pool.acquire() as conn:
            # Get totals (same logic as get_summary endpoint)
            totals = {
                "totalMessages": 0,
                "unread": 0,
                "leads": 0,
                "complaints": 0,
                "urgent": 0,
                "highPriority": 0,
            }
            
            # Get message totals
            msg_row = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN processed = false THEN 1 END) as unread
                FROM messages
                """
            )
            totals["totalMessages"] = int(msg_row["total"]) if msg_row else 0
            totals["unread"] = int(msg_row["unread"]) if msg_row else 0
            
            # Get leads count
            leads_row = await conn.fetchrow(
                """
                SELECT COUNT(*) as count 
                FROM contacts 
                WHERE tags IS NOT NULL
                  AND (
                    tags @> '"new-lead"'::jsonb
                    OR tags @> '"potential-interest"'::jsonb
                  )
                """
            )
            totals["leads"] = int(leads_row["count"]) if leads_row else 0
            
            # Get complaints count
            complaints_row = await conn.fetchrow(
                """
                SELECT COUNT(DISTINCT COALESCE(c.id, m.contact_id)) as count
                FROM messages m
                LEFT JOIN contacts c ON m.contact_id = c.id
                WHERE (c.tags IS NOT NULL AND c.tags @> '"escalation"'::jsonb)
                   OR (LOWER(m.body) LIKE '%complaint%' 
                       OR LOWER(m.body) LIKE '%refund%'
                       OR LOWER(m.body) LIKE '%dissatisfied%'
                       OR LOWER(m.body) LIKE '%unacceptable%'
                       OR LOWER(m.body) LIKE '%cancel%'
                       OR LOWER(m.body) LIKE '%speak to manager%')
                """
            )
            totals["complaints"] = int(complaints_row["count"]) if complaints_row else 0
            
            # Get urgent count
            urgent_row = await conn.fetchrow(
                """
                SELECT COUNT(DISTINCT c.id) as count
                FROM contacts c
                WHERE c.tags IS NOT NULL
                  AND c.tags @> '"urgent-action-required"'::jsonb
                """
            )
            totals["urgent"] = int(urgent_row["count"]) if urgent_row else 0
            
            # Get high priority count
            high_priority_row = await conn.fetchrow(
                """
                SELECT COUNT(DISTINCT c.id) as count
                FROM contacts c
                WHERE c.tags IS NOT NULL
                  AND c.tags @> '"high-priority"'::jsonb
                """
            )
            totals["highPriority"] = int(high_priority_row["count"]) if high_priority_row else 0
            
            # Get tasks
            try:
                task_rows = await conn.fetch(
                    """
                    SELECT 
                        t.*,
                        c.name as contact_name,
                        c.email as contact_email,
                        c.tags as contact_tags,
                        c.company as contact_company,
                        COALESCE(
                            t.thread_id,
                            (SELECT thread_id FROM messages m WHERE m.contact_id = t.contact_id ORDER BY m.created_at DESC LIMIT 1)
                        ) as thread_id,
                        COALESCE(
                            t.message_id,
                            (SELECT id FROM messages m WHERE m.contact_id = t.contact_id ORDER BY m.created_at DESC LIMIT 1)
                        ) as message_id,
                        (SELECT body FROM messages m WHERE m.contact_id = t.contact_id ORDER BY m.created_at DESC LIMIT 1) as latest_message_body
                    FROM tasks t
                    LEFT JOIN contacts c ON t.contact_id = c.id
                    WHERE t.status = 'pending'
                    ORDER BY t.due_at ASC NULLS LAST, t.created_at DESC
                    LIMIT 50
                    """
                )
            except Exception:
                task_rows = await conn.fetch(
                    """
                    SELECT 
                        t.*,
                        c.name as contact_name,
                        c.email as contact_email,
                        c.tags as contact_tags,
                        c.company as contact_company,
                        (SELECT thread_id FROM messages m WHERE m.contact_id = t.contact_id ORDER BY m.created_at DESC LIMIT 1) as thread_id,
                        (SELECT id FROM messages m WHERE m.contact_id = t.contact_id ORDER BY m.created_at DESC LIMIT 1) as message_id,
                        (SELECT body FROM messages m WHERE m.contact_id = t.contact_id ORDER BY m.created_at DESC LIMIT 1) as latest_message_body
                    FROM tasks t
                    LEFT JOIN contacts c ON t.contact_id = c.id
                    WHERE t.status = 'pending'
                    ORDER BY t.due_at ASC NULLS LAST, t.created_at DESC
                    LIMIT 50
                    """
                )
            
            # Compute priority for each task
            from app.lib.priority import compute_priority
            tasks = []
            for row in task_rows:
                task = dict(row)
                contact_tags = task.get("contact_tags")
                if isinstance(contact_tags, str):
                    try:
                        contact_tags = json.loads(contact_tags)
                    except:
                        contact_tags = []
                elif not isinstance(contact_tags, list):
                    contact_tags = []
                
                priority = compute_priority({
                    "task": {
                        "due_at": task.get("due_at"),
                        "title": task.get("title"),
                        "status": task.get("status"),
                    },
                    "message": {
                        "body": task.get("latest_message_body") or "",
                    },
                    "contact": {
                        "tags": contact_tags,
                        "last_order_amount": 0,
                    },
                })
                
                task["priority"] = priority
                tasks.append(task)
            
            # Group tasks by priority
            tasks_by_priority = {
                "P0": [t for t in tasks if t.get("priority") == "P0"][:6],
                "P1": [t for t in tasks if t.get("priority") == "P1"][:6],
                "P2": [t for t in tasks if t.get("priority") == "P2"][:6],
            }
            
            counts = {
                "P0": len([t for t in tasks if t.get("priority") == "P0"]),
                "P1": len([t for t in tasks if t.get("priority") == "P1"]),
                "P2": len([t for t in tasks if t.get("priority") == "P2"]),
            }
            
            # Get top leads
            lead_rows = await conn.fetch(
                """
                SELECT 
                    c.id,
                    c.name,
                    c.email,
                    c.company,
                    c.tags,
                    (SELECT COUNT(*) FROM messages m WHERE m.contact_id = c.id) as message_count
                FROM contacts c
                WHERE c.tags IS NOT NULL
                  AND (
                    c.tags @> '"new-lead"'::jsonb
                    OR c.tags @> '"potential-interest"'::jsonb
                  )
                ORDER BY c.created_at DESC
                LIMIT 6
                """
            )
            
            top_leads = [
                {
                    "id": str(row["id"]),
                    "name": row["name"],
                    "company": row.get("company"),
                    "email": row["email"],
                    "message_count": int(row["message_count"]) if row["message_count"] else 0,
                    "last_order_amount": 0,
                }
                for row in lead_rows
            ]
            
            # Get performance metrics
            performance = {
                "avgLatencyMs": None,
                "suggestionsGenerated": 0,
                "acceptanceRate": 0,
                "messagesSent": 0,
            }
            
            try:
                latency_row = await conn.fetchrow(
                    """
                    SELECT AVG(latency_ms) as avg_latency 
                    FROM events 
                    WHERE latency_ms IS NOT NULL 
                    AND type = 'suggestion_generated'
                    """
                )
                performance["avgLatencyMs"] = (
                    round(float(latency_row["avg_latency"])) if latency_row and latency_row["avg_latency"] else None
                )
                
                sugg_row = await conn.fetchrow("SELECT COUNT(*) as count FROM suggestions")
                performance["suggestionsGenerated"] = int(sugg_row["count"]) if sugg_row else 0
                
                accepted_row = await conn.fetchrow(
                    """
                    SELECT COUNT(*) as count 
                    FROM suggestions 
                    WHERE final_text IS NOT NULL 
                    AND final_text = model_response 
                    AND edited = false
                    """
                )
                accepted = int(accepted_row["count"]) if accepted_row else 0
                performance["acceptanceRate"] = (
                    round((accepted / performance["suggestionsGenerated"]) * 100) / 100
                    if performance["suggestionsGenerated"] > 0
                    else 0
                )
                
                sent_row = await conn.fetchrow("SELECT COUNT(*) as count FROM events WHERE type = 'message_sent'")
                performance["messagesSent"] = int(sent_row["count"]) if sent_row else 0
            except Exception as error:
                print(f"[CacheRefresh] Could not fetch performance metrics: {error}")
            
            # Get top P0 task for context
            top_p0_task = tasks_by_priority["P0"][0] if tasks_by_priority["P0"] else None
            urgent_context = (
                {
                    "contactName": top_p0_task.get("contact_name") or "A customer",
                    "taskTitle": top_p0_task.get("title") or "",
                    "messageBody": top_p0_task.get("latest_message_body") or "",
                }
                if top_p0_task
                else None
            )
            
            # Cache badges/metrics immediately
            badges_data = {
                "totals": totals,
                "tasks": {
                    "counts": counts,
                },
                "performance": performance,
            }
            set_badges_cache(badges_data)
            
            # Generate AI summary - import the function directly
            from app.routes import summary as summary_module
            await summary_module._generate_summary_async(totals, tasks_by_priority, counts, top_leads, urgent_context)
            
    except Exception as e:
        print(f"[CacheRefresh] Error generating dashboard summary: {e}")
        import traceback
        traceback.print_exc()

