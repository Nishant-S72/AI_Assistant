"""Summary routes."""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from datetime import datetime
from app.db.connection import get_pool
from app.clients.llm import generate_chat_completion, LLMMessage, LLMRequestOptions
from app.lib.priority import compute_priority
import json
import os

router = APIRouter()

# Simple in-memory cache
_summary_cache = {}
_summary_cache_timestamp = None


@router.get("")
async def get_summary():
    """Get inbox summary with totals, tasks, and LLM-generated summary."""
    start_time = datetime.now().timestamp() * 1000

    try:
        pool = await get_pool()
        db_available = False

        try:
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_available = True
        except Exception:
            pass

        totals = {
            "totalMessages": 0,
            "unread": 0,
            "leads": 0,
            "complaints": 0,
        }

        tasks: List[Dict] = []
        top_leads: List[Dict] = []

        if db_available:
            async with pool.acquire() as conn:
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
                    "SELECT COUNT(*) as count FROM contacts WHERE tags::text LIKE '%lead%'"
                )
                totals["leads"] = int(leads_row["count"]) if leads_row else 0

                # Get complaints count
                complaints_row = await conn.fetchrow(
                    """
                    SELECT COUNT(DISTINCT thread_id) as count
                    FROM messages
                    WHERE LOWER(body) LIKE '%complaint%' 
                       OR LOWER(body) LIKE '%delay%'
                       OR LOWER(body) LIKE '%late%'
                    """
                )
                totals["complaints"] = int(complaints_row["count"]) if complaints_row else 0

                # Get tasks
                task_rows = await conn.fetch(
                    """
                    SELECT 
                        t.*,
                        c.name as contact_name,
                        c.email as contact_email,
                        c.tags as contact_tags,
                        c.company as contact_company,
                        (SELECT body FROM messages m WHERE m.contact_id = t.contact_id ORDER BY m.created_at DESC LIMIT 1) as latest_message_body,
                        (SELECT id FROM messages m WHERE m.contact_id = t.contact_id ORDER BY m.created_at DESC LIMIT 1) as latest_message_id,
                        (SELECT thread_id FROM messages m WHERE m.contact_id = t.contact_id ORDER BY m.created_at DESC LIMIT 1) as thread_id
                    FROM tasks t
                    LEFT JOIN contacts c ON t.contact_id = c.id
                    WHERE t.status = 'pending'
                    ORDER BY t.due_at ASC NULLS LAST, t.created_at DESC
                    LIMIT 50
                    """
                )

                # Compute priority for each task
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

                    priority = compute_priority(
                        {
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
                        }
                    )

                    task["priority"] = priority
                    tasks.append(task)

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
                    WHERE c.tags::text LIKE '%lead%'
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

        # Get performance metrics
        performance = {
            "avgLatencyMs": None,
            "suggestionsGenerated": 0,
            "acceptanceRate": 0,
            "messagesSent": 0,
        }

        if db_available:
            try:
                async with pool.acquire() as conn:
                    # Average latency
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

                    # Suggestions generated
                    sugg_row = await conn.fetchrow("SELECT COUNT(*) as count FROM suggestions")
                    performance["suggestionsGenerated"] = int(sugg_row["count"]) if sugg_row else 0

                    # Acceptance rate
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

                    # Messages sent
                    sent_row = await conn.fetchrow("SELECT COUNT(*) as count FROM events WHERE type = 'message_sent'")
                    performance["messagesSent"] = int(sent_row["count"]) if sent_row else 0
            except Exception as error:
                print(f"Could not fetch performance metrics: {error}")

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

        # Generate LLM summary
        summary_paragraph = ""
        summary_generating = False

        # Check cache
        global _summary_cache, _summary_cache_timestamp
        if _summary_cache and _summary_cache_timestamp:
            cache_age = (datetime.now().timestamp() * 1000) - _summary_cache_timestamp
            if cache_age < 60000:  # 1 minute cache
                summary_paragraph = _summary_cache
                summary_generating = False

        # Generate if not cached
        if not summary_paragraph:
            try:
                top_p0_tasks = ", ".join(
                    [f"{t.get('contact_name', 'Contact')}: {t.get('title', '')}" for t in tasks_by_priority["P0"][:3]]
                )
                top_leads_list = ", ".join(
                    [f"{l['name']}{' from ' + l['company'] if l.get('company') else ''}" for l in top_leads[:3]]
                )

                urgent_msg = ""
                if urgent_context:
                    msg_body = urgent_context.get("messageBody", "")
                    if msg_body:
                        urgent_msg = f'Most urgent: {urgent_context["contactName"]} has {urgent_context["taskTitle"]}. Their message: "{msg_body[:200]}"'
                    else:
                        urgent_msg = f'Most urgent: {urgent_context["contactName"]} has {urgent_context["taskTitle"]}.'
                
                summary_prompt = f"""Here's what's in the inbox right now:

{totals['totalMessages']} total messages, {totals['unread']} unread. {totals['leads']} potential leads, {totals['complaints']} complaints flagged.

{counts['P0']} urgent tasks (P0) need immediate attention{' - including: ' + top_p0_tasks if top_p0_tasks else ''}. {counts['P1']} high-priority tasks (P1) due soon. {counts['P2']} normal tasks.

{urgent_msg}

{'Top leads: ' + top_leads_list + '.' if top_leads else ''}

Give me a concise summary of what's happening. Be specific about who needs attention and why. Keep it brief - under 250 words."""

                llm_response = await generate_chat_completion(
                    LLMRequestOptions(
                        model=os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or "tinyllama",
                        messages=[
                            LLMMessage(
                                "system",
                                "You're briefing someone about their inbox. Be natural, specific, and concise. Mention actual people and situations. No generic statements. Keep it under 250 words - be direct and brief.",
                            ),
                            LLMMessage("user", summary_prompt),
                        ],
                        temperature=0.7,
                        max_tokens=200,
                        use_local=os.getenv("USE_OLLAMA") != "false",
                    )
                )

                summary_paragraph = llm_response.content.strip()
                summary_generating = False

                # Cache for 1 minute
                _summary_cache = summary_paragraph
                _summary_cache_timestamp = datetime.now().timestamp() * 1000
            except Exception as error:
                print(f"[Summary] Failed to generate LLM summary: {error}")
                summary_paragraph = ""
                summary_generating = False

        # Generate category summaries using LLM
        category_summaries = {}
        for priority in ["P0", "P1", "P2"]:
            priority_tasks = tasks_by_priority.get(priority, [])
            if priority_tasks:
                try:
                    task_list = "\n".join(
                        [
                            f"- {t.get('contact_name', 'Contact')}: {t.get('title', '')}"
                            for t in priority_tasks[:5]
                        ]
                    )
                    context_prompt = f"""Tasks in {priority} priority:
{task_list}

Summarize what needs attention in this priority level. Be specific and concise. Under 100 words."""

                    llm_response = await generate_chat_completion(
                        LLMRequestOptions(
                            model=os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or "tinyllama",
                            messages=[
                                LLMMessage("system", "Summarize task priorities concisely."),
                                LLMMessage("user", context_prompt),
                            ],
                            temperature=0.7,
                            max_tokens=120,
                            use_local=os.getenv("USE_OLLAMA") != "false",
                        )
                    )

                    category_summaries[priority] = llm_response.content.strip()
                except Exception:
                    category_summaries[priority] = f"{len(priority_tasks)} {priority} priority tasks need attention."

        response_time = (datetime.now().timestamp() * 1000) - start_time

        return {
            "totals": totals,
            "tasks": {
                "counts": counts,
                "P0": tasks_by_priority.get("P0", []),
                "P1": tasks_by_priority.get("P1", []),
                "P2": tasks_by_priority.get("P2", []),
                "byPriority": tasks_by_priority,
                "categorySummaries": category_summaries,
            },
            "topLeads": top_leads,
            "performance": performance,
            "summaryParagraph": summary_paragraph,
            "summaryGenerating": summary_generating,
        }
    except Exception as error:
        print(f"Error generating summary: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(error)}")

