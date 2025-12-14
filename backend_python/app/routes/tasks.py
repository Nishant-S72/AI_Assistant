"""Task routes."""
from fastapi import APIRouter, HTTPException, Query, Body, BackgroundTasks
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.db.connection import get_pool
from app.lib.priority import compute_priority, compute_priority_with_reason
from app.services.task_inference import infer_tasks_from_messages
from app.core.logger import logger
import json
import uuid


class CreateTaskRequest(BaseModel):
    """Request model for creating a task."""
    contact_id: Optional[str] = None
    thread_id: Optional[str] = None
    message_id: Optional[str] = None
    title: str
    due_at: Optional[str] = None
    status: str = "pending"

router = APIRouter()


@router.get("")
async def list_tasks(
    status: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = None,
):
    """List tasks with optional status filter. Tasks are inferred from inbox messages."""
    try:
        # Trigger background task inference if tasks are empty or stale
        pool = await get_pool()
        async with pool.acquire() as conn:
            task_count = await conn.fetchval("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
            if task_count == 0 and background_tasks:
                # Trigger background inference
                background_tasks.add_task(infer_tasks_from_messages)
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Check if thread_id and message_id columns exist
            columns_info = await conn.fetch("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'tasks' 
                AND column_name IN ('thread_id', 'message_id')
            """)
            existing_columns = {row['column_name'] for row in columns_info}
            
            # Build SELECT query based on available columns
            if 'thread_id' in existing_columns and 'message_id' in existing_columns:
                query = """
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
                """
            else:
                # Fallback query without thread_id/message_id columns
                query = """
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
                """

            if status:
                query += " WHERE t.status = $1"

            query += " ORDER BY t.created_at DESC"

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

            priority, reason = compute_priority_with_reason(
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
            task["priority_reason"] = reason  # Add reason field for UI display
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
            # Check if thread_id and message_id columns exist
            columns_info = await conn.fetch("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'tasks' 
                AND column_name IN ('thread_id', 'message_id')
            """)
            existing_columns = {row['column_name'] for row in columns_info}
            
            # Build INSERT query based on available columns
            if 'thread_id' in existing_columns and 'message_id' in existing_columns:
                row = await conn.fetchrow(
                    """
                    INSERT INTO tasks (contact_id, thread_id, message_id, title, due_at, status, reminder_enabled)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING *
                    """,
                    request.contact_id,
                    request.thread_id,
                    request.message_id,
                    request.title,
                    request.due_at,
                    request.status,
                    True if request.due_at else False,  # Enable reminder if due date is set
                )
            else:
                # Fallback for tables without thread_id/message_id columns
                row = await conn.fetchrow(
                    """
                    INSERT INTO tasks (contact_id, title, due_at, status, reminder_enabled)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING *
                    """,
                    request.contact_id,
                    request.title,
                    request.due_at,
                    request.status,
                    True if request.due_at else False,  # Enable reminder if due date is set
                )

            # Schedule reminder if due date is set
            if request.due_at and row.get("reminder_enabled"):
                from app.scheduler.apscheduler_manager import get_scheduler
                from datetime import datetime, timedelta
                
                try:
                    due_date = datetime.fromisoformat(request.due_at.replace("Z", "+00:00"))
                    reminder_time = due_date - timedelta(minutes=row.get("reminder_minutes_before", 60))
                    
                    scheduler = get_scheduler()
                    if scheduler:
                        from app.scheduler.apscheduler_manager import send_task_reminder
                        job_id = f"task_reminder_{row['id']}"
                        scheduler.add_job(
                            send_task_reminder,
                            'date',
                            run_date=reminder_time,
                            args=[str(row["id"]), request.title],
                            id=job_id,
                            replace_existing=True,
                        )
                except Exception as e:
                    print(f"[Tasks] Failed to schedule reminder: {e}")

            # Log event
            await conn.execute(
                """
                INSERT INTO events (type, payload) VALUES ($1, $2)
                """,
                "task_created",
                json.dumps({
                    "taskId": str(row["id"]),
                    "contactId": request.contact_id,
                    "threadId": request.thread_id,
                    "messageId": request.message_id,
                    "title": request.title,
                }),
            )

            return dict(row)
    except Exception as error:
        print(f"Error creating task: {error}")
        raise HTTPException(status_code=500, detail="Failed to create task")


@router.patch("/{task_id}/complete")
async def complete_task(task_id: str):
    """Mark a task as completed."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE tasks 
                SET status = 'completed', completed_at = NOW(), updated_at = NOW()
                WHERE id = $1
                RETURNING *
                """,
                task_id,
            )
            
            if not row:
                raise HTTPException(status_code=404, detail="Task not found")
            
            # Cancel any scheduled reminders
            from app.scheduler.apscheduler_manager import get_scheduler
            scheduler = get_scheduler()
            if scheduler:
                try:
                    scheduler.remove_job(f"task_reminder_{task_id}")
                except:
                    pass  # Job might not exist
            
            # Log event
            await conn.execute(
                """
                INSERT INTO events (type, payload) VALUES ($1, $2)
                """,
                "task_completed",
                json.dumps({
                    "taskId": str(row["id"]),
                    "title": row.get("title"),
                }),
            )
            
            return dict(row)
    except HTTPException:
        raise
    except Exception as error:
        print(f"Error completing task: {error}")
        raise HTTPException(status_code=500, detail="Failed to complete task")


@router.patch("/{task_id}/cancel")
async def cancel_task(task_id: str, reason: Optional[str] = Body(None)):
    """Cancel a task."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE tasks 
                SET status = 'cancelled', cancelled_at = NOW(), cancelled_reason = $2, updated_at = NOW()
                WHERE id = $1
                RETURNING *
                """,
                task_id,
                reason,
            )
            
            if not row:
                raise HTTPException(status_code=404, detail="Task not found")
            
            # Cancel any scheduled reminders
            from app.scheduler.apscheduler_manager import get_scheduler
            scheduler = get_scheduler()
            if scheduler:
                try:
                    scheduler.remove_job(f"task_reminder_{task_id}")
                except:
                    pass  # Job might not exist
            
            # Log event
            await conn.execute(
                """
                INSERT INTO events (type, payload) VALUES ($1, $2)
                """,
                "task_cancelled",
                json.dumps({
                    "taskId": str(row["id"]),
                    "title": row.get("title"),
                    "reason": reason,
                }),
            )
            
            return dict(row)
    except HTTPException:
        raise
    except Exception as error:
        print(f"Error cancelling task: {error}")
        raise HTTPException(status_code=500, detail="Failed to cancel task")


@router.patch("/{task_id}/postpone")
async def postpone_task(task_id: str, new_due_date: str = Body(...)):
    """Postpone a task to a new due date."""
    try:
        from datetime import datetime
        
        # Validate new due date
        try:
            new_due = datetime.fromisoformat(new_due_date.replace("Z", "+00:00"))
        except:
            raise HTTPException(status_code=400, detail="Invalid date format. Use ISO 8601 format.")
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Get current task
            current = await conn.fetchrow("SELECT * FROM tasks WHERE id = $1", task_id)
            if not current:
                raise HTTPException(status_code=404, detail="Task not found")
            
            # Update task
            row = await conn.fetchrow(
                """
                UPDATE tasks 
                SET due_at = $1, postponed_until = $1, updated_at = NOW(), reminder_sent = FALSE
                WHERE id = $2
                RETURNING *
                """,
                new_due,
                task_id,
            )
            
            # Reschedule reminder
            if row.get("reminder_enabled"):
                from app.scheduler.apscheduler_manager import get_scheduler
                from datetime import timedelta
                
                reminder_time = new_due - timedelta(minutes=row.get("reminder_minutes_before", 60))
                
                scheduler = get_scheduler()
                if scheduler:
                    from app.scheduler.apscheduler_manager import send_task_reminder
                    job_id = f"task_reminder_{task_id}"
                    try:
                        scheduler.remove_job(job_id)  # Remove old reminder
                    except:
                        pass
                    
                    scheduler.add_job(
                        send_task_reminder,
                        'date',
                        run_date=reminder_time,
                        args=[str(row["id"]), row.get("title")],
                        id=job_id,
                        replace_existing=True,
                    )
            
            # Log event
            await conn.execute(
                """
                INSERT INTO events (type, payload) VALUES ($1, $2)
                """,
                "task_postponed",
                json.dumps({
                    "taskId": str(row["id"]),
                    "title": row.get("title"),
                    "oldDueDate": current.get("due_at").isoformat() if current.get("due_at") else None,
                    "newDueDate": new_due.isoformat(),
                }),
            )
            
            return dict(row)
    except HTTPException:
        raise
    except Exception as error:
        print(f"Error postponing task: {error}")
        raise HTTPException(status_code=500, detail="Failed to postpone task")


@router.get("/reminders")
async def get_task_reminders():
    """Get tasks with upcoming reminders (for main screen display)."""
    try:
        from datetime import datetime, timedelta
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Get tasks with reminders enabled, due within next 7 days, not completed/cancelled
            now = datetime.now()
            seven_days_later = now + timedelta(days=7)
            
            rows = await conn.fetch(
                """
                SELECT 
                    t.*,
                    c.name as contact_name,
                    c.email as contact_email
                FROM tasks t
                LEFT JOIN contacts c ON t.contact_id = c.id
                WHERE t.reminder_enabled = TRUE
                  AND t.status = 'pending'
                  AND t.due_at IS NOT NULL
                  AND t.due_at >= $1
                  AND t.due_at <= $2
                  AND (t.reminder_sent = FALSE OR t.reminder_sent_at IS NULL)
                ORDER BY t.due_at ASC
                LIMIT 20
                """,
                now,
                seven_days_later,
            )
            
            tasks = []
            for row in rows:
                task = dict(row)
                # Calculate time until due
                due_date = row.get("due_at")
                if due_date:
                    if isinstance(due_date, str):
                        due_date = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
                    time_until = due_date - now
                    task["time_until_due"] = {
                        "days": time_until.days,
                        "hours": time_until.seconds // 3600,
                        "minutes": (time_until.seconds % 3600) // 60,
                    }
                tasks.append(task)
            
            return tasks
    except Exception as error:
        print(f"Error fetching task reminders: {error}")
        raise HTTPException(status_code=500, detail="Failed to fetch task reminders")

