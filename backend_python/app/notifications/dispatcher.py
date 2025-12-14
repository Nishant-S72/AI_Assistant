"""Notification dispatcher for reminders and tasks with duplicate prevention."""
from typing import Optional
import hashlib
from datetime import datetime
from app.notifications.email_adapter import send_email_notification
from app.notifications.slack_adapter import send_slack_notification
from app.notifications.inapp_adapter import send_inapp_notification
from app.db.connection import get_pool
from app.core.logger import logger
import asyncio


async def send_reminder_notification(
    reminder_id: str,
    user_id: str,
    event_id: Optional[str],
    channel: str,
    message: Optional[str],
):
    """
    Send reminder notification via specified channel with duplicate prevention.
    
    Uses hashed delivery keys to prevent duplicate notifications.
    """
    try:
        # Generate delivery key to prevent duplicates
        delivery_key = hashlib.md5(
            f"{reminder_id}:{user_id}:{event_id}:{channel}:{message}".encode()
        ).hexdigest()
        
        # Check if already delivered
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Check reminders table for delivered status
            delivered = await conn.fetchval(
                """
                SELECT delivered FROM reminders 
                WHERE id = $1 AND delivered = TRUE
                """,
                reminder_id,
            )
            
            if delivered:
                logger.info(
                    "Reminder already delivered, skipping",
                    extra={"reminder_id": reminder_id, "delivery_key": delivery_key}
                )
                return
        
        # Send notification
        if channel == "email":
            await send_email_notification(user_id, message or "Reminder", message or "")
        elif channel == "slack":
            await send_slack_notification(user_id, message or "Reminder", message or "")
        else:
            await send_inapp_notification(user_id, message or "Reminder", message or "")
        
        # Mark as delivered
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE reminders 
                SET delivered = TRUE, delivered_at = NOW()
                WHERE id = $1
                """,
                reminder_id,
            )
        
        logger.info(
            "Reminder notification sent",
            extra={"reminder_id": reminder_id, "channel": channel, "delivery_key": delivery_key}
        )
    except Exception as e:
        logger.error(
            "Error sending reminder notification",
            extra={"reminder_id": reminder_id, "error": str(e)}
        )
        # Retry once after failure
        try:
            await asyncio.sleep(1)
            if channel == "email":
                await send_email_notification(user_id, message or "Reminder", message or "")
            elif channel == "slack":
                await send_slack_notification(user_id, message or "Reminder", message or "")
            else:
                await send_inapp_notification(user_id, message or "Reminder", message or "")
            logger.info("Reminder notification sent on retry", extra={"reminder_id": reminder_id})
        except Exception as retry_error:
            logger.error(
                "Reminder notification failed on retry",
                extra={"reminder_id": reminder_id, "error": str(retry_error)}
            )


async def send_task_reminder_notification(
    task_id: str,
    user_id: str,
    message: Optional[str],
):
    """
    Send task reminder notification with duplicate prevention.
    
    Uses hashed delivery keys to prevent duplicate notifications.
    """
    try:
        # Generate delivery key to prevent duplicates
        delivery_key = hashlib.md5(
            f"task:{task_id}:{user_id}:{message}".encode()
        ).hexdigest()
        
        # Check if already delivered
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Check tasks table for reminder_sent status
            reminder_sent = await conn.fetchval(
                """
                SELECT reminder_sent FROM tasks 
                WHERE id = $1 AND reminder_sent = TRUE
                """,
                task_id,
            )
            
            if reminder_sent:
                logger.info(
                    "Task reminder already sent, skipping",
                    extra={"task_id": task_id, "delivery_key": delivery_key}
                )
                return
        
        # Send notification
        await send_inapp_notification(user_id, message or "Task reminder", message or "")
        
        # Mark as sent
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE tasks 
                SET reminder_sent = TRUE, reminder_sent_at = NOW()
                WHERE id = $1
                """,
                task_id,
            )
        
        logger.info(
            "Task reminder notification sent",
            extra={"task_id": task_id, "delivery_key": delivery_key}
        )
    except Exception as e:
        logger.error(
            "Error sending task reminder notification",
            extra={"task_id": task_id, "error": str(e)}
        )
        # Retry once after failure
        try:
            await asyncio.sleep(1)
            await send_inapp_notification(user_id, message or "Task reminder", message or "")
            logger.info("Task reminder notification sent on retry", extra={"task_id": task_id})
        except Exception as retry_error:
            logger.error(
                "Task reminder notification failed on retry",
                extra={"task_id": task_id, "error": str(retry_error)}
            )
