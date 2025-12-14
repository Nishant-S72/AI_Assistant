"""
Calendar service for creating calendar events.
"""
from typing import Optional, List, Dict, Any
from app.core.errors import ValidationError
from app.core.logger import logger
# Note: Avoid circular import - create event directly via DB
import uuid


async def create_calendar_event(
    title: str,
    start_time: str,
    end_time: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    location: Optional[str] = None,
    description: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a calendar event.
    
    Args:
        title: Event title
        start_time: Start time (ISO 8601)
        end_time: End time (ISO 8601)
        attendees: List of attendee emails
        location: Event location
        description: Event description
        user_id: User ID
    
    Returns:
        {"id": str, "title": str, "start": str, "end": str}
    """
    # Validate
    if not title or not start_time:
        raise ValidationError("title and start_time are required")
    
    # Create event directly via database to avoid circular imports
    
    from app.db.connection import get_pool
    from datetime import datetime
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat((end_time or start_time).replace("Z", "+00:00"))
        
        row = await conn.fetchrow(
            """
            INSERT INTO events 
            (user_id, title, description, location, start, "end", attendees_json)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, title, start, "end"
            """,
            user_id or "00000000-0000-0000-0000-000000000000",
            title,
            description,
            location,
            start_dt,
            end_dt,
            '[]' if not attendees else str([{"email": e} for e in attendees]),
        )
    
    event_id = str(row["id"])
    
    logger.info(
        "Calendar event created",
        extra={
            "event_id": event_id,
            "title": title,
            "user_id": user_id,
        }
    )
    
    return {
        "id": event_id,
        "title": title,
        "start": start_time,
        "end": end_time or start_time,
    }

