"""
Tasks service for creating tasks.
"""
from typing import Optional, Dict, Any
from app.core.errors import ValidationError
from app.core.logger import logger
from app.db.connection import get_pool
import uuid
from datetime import datetime


async def create_task(
    title: str,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    contact_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a task.
    
    Args:
        title: Task title
        description: Task description
        due_date: Due date (ISO 8601)
        priority: Priority (P0, P1, P2, FYI)
        contact_id: Associated contact ID
        user_id: User ID
    
    Returns:
        {"id": str, "title": str, "status": str}
    """
    # Validate
    if not title:
        raise ValidationError("title is required")
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        due_at = None
        if due_date:
            try:
                due_at = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
            except:
                pass
        
        row = await conn.fetchrow(
            """
            INSERT INTO tasks 
            (user_id, title, description, due_at, priority, contact_id, status)
            VALUES ($1, $2, $3, $4, $5, $6, 'pending')
            RETURNING id, title, status
            """,
            user_id or "00000000-0000-0000-0000-000000000000",
            title,
            description,
            due_at,
            priority,
            contact_id,
        )
    
    task_id = str(row["id"])
    
    logger.info(
        "Task created",
        extra={
            "task_id": task_id,
            "title": title,
            "priority": priority,
            "user_id": user_id,
        }
    )
    
    return {
        "id": task_id,
        "title": title,
        "status": row["status"],
    }

