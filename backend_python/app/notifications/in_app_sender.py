"""In-app notification sender (SSE)."""
from datetime import datetime
from typing import Optional, Dict, Any
from app.notifications.sse_manager import send_sse_notification


async def send_in_app_notification(
    user_id: str,
    event_title: str,
    event_start: datetime,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send in-app notification via SSE.
    
    Args:
        user_id: User ID
        event_title: Event title
        event_start: Event start time
        message: Custom message
    
    Returns:
        Dict with send status
    """
    notification_text = message or f"Reminder: {event_title} starts at {event_start.strftime('%Y-%m-%d %H:%M')}"
    
    await send_sse_notification(
        user_id=user_id,
        notification={
            "type": "reminder",
            "title": event_title,
            "message": notification_text,
            "event_start": event_start.isoformat(),
        }
    )
    
    return {"success": True, "user_id": user_id}


