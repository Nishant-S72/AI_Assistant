"""Notification dispatcher for sending reminders via multiple channels."""
from typing import Optional, Dict, Any
from app.notifications.email_sender import send_email_reminder
from app.notifications.slack_sender import send_slack_reminder
from app.notifications.in_app_sender import send_in_app_notification
from app.db.connection import get_pool


async def send_reminder_notification(
    reminder_id: str,
    user_id: str,
    event_id: str,
    reminder_type: str,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send a reminder notification via the specified channel.
    
    Args:
        reminder_id: Reminder ID
        user_id: User ID
        event_id: Event ID
        reminder_type: Type of reminder ('email', 'slack', 'in_app')
        message: Custom message
    
    Returns:
        Dict with notification status
    """
    pool = await get_pool()
    
    # Get event details
    async with pool.acquire() as conn:
        event_row = await conn.fetchrow(
            """
            SELECT title, start_time, end_time
            FROM event_mirror
            WHERE id = $1
            """,
            event_id,
        )
        
        if not event_row:
            print(f"[Notification] Event {event_id} not found")
            return {"success": False, "error": "Event not found"}
        
        # Get user details
        user_row = await conn.fetchrow(
            """
            SELECT email, name
            FROM users
            WHERE id = $1
            """,
            user_id,
        )
        
        if not user_row:
            print(f"[Notification] User {user_id} not found")
            return {"success": False, "error": "User not found"}
        
        # Send notification based on type
        try:
            if reminder_type == "email":
                result = await send_email_reminder(
                    to_email=user_row["email"],
                    event_title=event_row["title"],
                    event_start=event_row["start_time"],
                    message=message,
                )
            elif reminder_type == "slack":
                result = await send_slack_reminder(
                    user_id=user_id,
                    event_title=event_row["title"],
                    event_start=event_row["start_time"],
                    message=message,
                )
            elif reminder_type == "in_app":
                result = await send_in_app_notification(
                    user_id=user_id,
                    event_title=event_row["title"],
                    event_start=event_row["start_time"],
                    message=message,
                )
            else:
                raise ValueError(f"Unknown reminder type: {reminder_type}")
            
            # Update reminder status
            await conn.execute(
                """
                UPDATE reminders
                SET status = 'sent', last_attempt_at = NOW(), updated_at = NOW()
                WHERE id = $1
                """,
                reminder_id,
            )
            
            return {"success": True, "reminder_id": reminder_id, **result}
            
        except Exception as e:
            print(f"[Notification] Error sending reminder {reminder_id}: {e}")
            
            # Update reminder with error
            await conn.execute(
                """
                UPDATE reminders
                SET status = 'failed', error_message = $1, last_attempt_at = NOW(), updated_at = NOW()
                WHERE id = $2
                """,
                str(e),
                reminder_id,
            )
            
            return {"success": False, "error": str(e)}


