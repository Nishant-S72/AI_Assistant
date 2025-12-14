"""Service to infer tasks from inbox messages."""
from typing import List, Dict, Any, Optional
from app.db.connection import get_pool
from app.clients.llm import generate_chat_completion, LLMMessage, LLMRequestOptions
import os
import json
import uuid
from datetime import datetime


async def infer_tasks_from_messages(contact_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Infer tasks from inbox messages using LLM.
    
    Args:
        contact_id: Optional contact ID to filter messages
        limit: Maximum number of messages to analyze
    
    Returns:
        List of inferred task dictionaries
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Get recent messages that might contain actionable items
            if contact_id:
                messages_query = """
                    SELECT m.id, m.thread_id, m.contact_id, m.sender, m.body, m.created_at,
                           c.name as contact_name, c.email as contact_email, c.tags as contact_tags
                    FROM messages m
                    JOIN contacts c ON m.contact_id = c.id
                    WHERE m.contact_id = $1
                    ORDER BY m.created_at DESC
                    LIMIT $2
                """
                rows = await conn.fetch(messages_query, contact_id, limit)
            else:
                messages_query = """
                    SELECT m.id, m.thread_id, m.contact_id, m.sender, m.body, m.created_at,
                           c.name as contact_name, c.email as contact_email, c.tags as contact_tags
                    FROM messages m
                    JOIN contacts c ON m.contact_id = c.id
                    WHERE m.sender = 'contact'
                    ORDER BY m.created_at DESC
                    LIMIT $1
                """
                rows = await conn.fetch(messages_query, limit)
            
            if not rows:
                return []
            
            # Group messages by thread
            threads = {}
            for row in rows:
                thread_id = row['thread_id']
                if thread_id not in threads:
                    threads[thread_id] = {
                        'thread_id': thread_id,
                        'contact_id': row['contact_id'],
                        'contact_name': row['contact_name'],
                        'contact_email': row['contact_email'],
                        'contact_tags': row['contact_tags'],
                        'messages': []
                    }
                threads[thread_id]['messages'].append({
                    'sender': row['sender'],
                    'body': row['body'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                })
            
            # Analyze each thread for actionable tasks
            inferred_tasks = []
            for thread_data in list(threads.values())[:50]:  # Limit to 50 threads
                tasks = await _extract_tasks_from_thread(thread_data)
                inferred_tasks.extend(tasks)
            
            # Save inferred tasks to database
            saved_count = await _save_inferred_tasks(inferred_tasks, pool)
            
            print(f"[TaskInference] Inferred {len(inferred_tasks)} tasks, saved {saved_count} new tasks")
            return saved_count
            
    except Exception as e:
        print(f"[TaskInference] Error inferring tasks: {e}")
        import traceback
        traceback.print_exc()
        return 0


async def _extract_tasks_from_thread(thread_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract tasks from a thread using LLM."""
    try:
        # Build context from thread messages
        messages_text = "\n".join([
            f"{msg['sender']}: {msg['body']}"
            for msg in thread_data['messages']
        ])
        
        prompt = f"""Analyze the following conversation thread and extract any actionable tasks that need to be completed.

Conversation:
{messages_text}

Instructions:
- Identify specific, actionable tasks (e.g., "Follow up on pricing", "Send refund", "Schedule meeting")
- Only extract tasks that are explicitly mentioned or clearly implied
- Return tasks in JSON format: [{{"title": "Task title", "due_at": "YYYY-MM-DD or null", "priority": "high/medium/low"}}]
- If no tasks found, return empty array []
- Be concise and specific

JSON:"""
        
        response = await generate_chat_completion(
            LLMRequestOptions(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    LLMMessage("system", "You are a task extraction assistant. Extract actionable tasks from conversations and return only valid JSON arrays."),
                    LLMMessage("user", prompt),
                ],
                max_tokens=500,
                temperature=0.3,
            )
        )
        
        # Parse JSON response
        content = response.content.strip()
        # Remove markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        try:
            tasks = json.loads(content)
            if not isinstance(tasks, list):
                tasks = []
        except json.JSONDecodeError:
            print(f"[TaskInference] Failed to parse JSON: {content[:200]}")
            tasks = []
        
        # Enrich tasks with thread context
        enriched_tasks = []
        for task in tasks:
            if isinstance(task, dict) and task.get("title"):
                enriched_tasks.append({
                    "title": task["title"],
                    "contact_id": thread_data["contact_id"],
                    "thread_id": thread_data["thread_id"],
                    "message_id": thread_data["messages"][0].get("id") if thread_data["messages"] else None,
                    "due_at": task.get("due_at"),
                    "status": "pending",
                    "priority": task.get("priority", "medium"),
                })
        
        return enriched_tasks
        
    except Exception as e:
        print(f"[TaskInference] Error extracting tasks from thread: {e}")
        return []


async def _save_inferred_tasks(tasks: List[Dict[str, Any]], pool) -> int:
    """Save inferred tasks to database, avoiding duplicates. Returns count of saved tasks."""
    if not tasks:
        return 0
    
    saved_count = 0
    
    try:
        async with pool.acquire() as conn:
            # Check which columns exist
            columns_info = await conn.fetch("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'tasks' 
                AND column_name IN ('thread_id', 'message_id')
            """)
            existing_columns = {row['column_name'] for row in columns_info}
            
            for task in tasks:
                # Check if task already exists (by title and contact_id)
                existing = await conn.fetchrow(
                    """
                    SELECT id FROM tasks 
                    WHERE title = $1 AND contact_id = $2 AND status = 'pending'
                    LIMIT 1
                    """,
                    task["title"],
                    task["contact_id"],
                )
                
                if existing:
                    continue  # Skip duplicates
                
                # Insert new task
                if 'thread_id' in existing_columns and 'message_id' in existing_columns:
                    result = await conn.execute(
                        """
                        INSERT INTO tasks (contact_id, thread_id, message_id, title, due_at, status)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT DO NOTHING
                        """,
                        task["contact_id"],
                        task.get("thread_id"),
                        task.get("message_id"),
                        task["title"],
                        task.get("due_at"),
                        task["status"],
                    )
                else:
                    result = await conn.execute(
                        """
                        INSERT INTO tasks (contact_id, title, due_at, status)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT DO NOTHING
                        """,
                        task["contact_id"],
                        task["title"],
                        task.get("due_at"),
                        task["status"],
                    )
                
                if result and "INSERT" in result:
                    saved_count += 1
        
        return saved_count
    except Exception as e:
        print(f"[TaskInference] Error saving tasks: {e}")
        return 0

