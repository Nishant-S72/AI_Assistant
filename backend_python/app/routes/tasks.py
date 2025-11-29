"""Task routes."""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.db.connection import get_pool
from app.lib.priority import compute_priority
import json
import uuid


class CreateTaskRequest(BaseModel):
    """Request model for creating a task."""
    contact_id: Optional[str] = None
    title: str
    due_at: Optional[str] = None
    status: str = "pending"

router = APIRouter()


@router.get("")
async def list_tasks(status: Optional[str] = Query(None)):
    """List tasks with optional status filter."""
    try:
        pool = await get_pool()
        query = """
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
        """

        if status:
            query += " WHERE t.status = $1"

        query += " ORDER BY t.created_at DESC"

        async with pool.acquire() as conn:
            if status:
                rows = await conn.fetch(query, status)
            else:
                rows = await conn.fetch(query)

        # Compute priority for each task
        tasks = []
        for row in rows:
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

        return tasks
    except Exception as error:
        print(f"Error fetching tasks: {error}")
        raise HTTPException(status_code=500, detail="Failed to fetch tasks")


@router.post("")
async def create_task(request: CreateTaskRequest):
    """Create a new task."""
    if not request.title:
        raise HTTPException(status_code=400, detail="Title is required")

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO tasks (contact_id, title, due_at, status)
                VALUES ($1, $2, $3, $4)
                RETURNING *
                """,
                request.contact_id,
                request.title,
                request.due_at,
                request.status,
            )

            # Log event
            await conn.execute(
                """
                INSERT INTO events (type, payload) VALUES ($1, $2)
                """,
                "task_created",
                json.dumps({
                    "taskId": str(row["id"]),
                    "contactId": request.contact_id,
                    "title": request.title,
                }),
            )

            return dict(row)
    except Exception as error:
        print(f"Error creating task: {error}")
        raise HTTPException(status_code=500, detail="Failed to create task")

