"""APScheduler manager for scheduling reminders."""
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from app.db.connection import get_pool
from app.notifications.dispatcher import send_reminder_notification

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """Get or create global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        # Use in-memory job store (can be upgraded to SQLAlchemyJobStore with SQLAlchemy)
        # TODO: For production, use SQLAlchemyJobStore with PostgreSQL
        jobstores = {
            "default": MemoryJobStore(),
        }
        executors = {
            "default": ThreadPoolExecutor(max_workers=10),
        }
        job_defaults = {
            "coalesce": True,
            "max_instances": 3,
        }
        
        _scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
        )
        _scheduler.start()
        print("[Scheduler] APScheduler started (using MemoryJobStore)")
    
    return _scheduler


async def schedule_reminder(
    reminder_id: str,
    trigger_time: datetime,
    user_id: str,
    event_id: str,
    reminder_type: str,
    message: Optional[str] = None,
) -> str:
    """
    Schedule a reminder job.
    
    Args:
        reminder_id: Reminder ID
        trigger_time: When to trigger the reminder
        user_id: User ID
        event_id: Event ID
        reminder_type: Type of reminder
        message: Reminder message
    
    Returns:
        Job ID
    """
    scheduler = get_scheduler()
    
    job_id = f"reminder_{reminder_id}"
    
    scheduler.add_job(
        send_reminder_notification,
        "date",
        run_date=trigger_time,
        id=job_id,
        args=[reminder_id, user_id, event_id, reminder_type, message],
        replace_existing=True,
    )
    
    print(f"[Scheduler] Scheduled reminder {reminder_id} for {trigger_time}")
    return job_id


async def schedule_reminders_for_event(
    event_id: str,
    user_id: str,
    event_start_time: datetime,
) -> None:
    """
    Schedule default reminders for an event.
    
    Args:
        event_id: Event ID
        user_id: User ID
        event_start_time: Event start time
    """
    pool = await get_pool()
    
    # Default reminders: 15 minutes and 1 hour before
    default_reminders = [
        {"minutes": 15, "type": "in_app"},
        {"minutes": 60, "type": "email"},
    ]
    
    for reminder_config in default_reminders:
        trigger_time = event_start_time - timedelta(minutes=reminder_config["minutes"])
        
        # Only schedule if trigger time is in the future
        if trigger_time > datetime.now():
            reminder_id = f"{event_id}_{reminder_config['minutes']}m"
            await schedule_reminder(
                reminder_id=reminder_id,
                trigger_time=trigger_time,
                user_id=user_id,
                event_id=event_id,
                reminder_type=reminder_config["type"],
            )


async def cancel_reminder_job(job_id: str) -> bool:
    """
    Cancel a reminder job.
    
    Args:
        job_id: APScheduler job ID
    
    Returns:
        True if job was cancelled, False if not found
    """
    scheduler = get_scheduler()
    try:
        scheduler.remove_job(job_id)
        print(f"[Scheduler] Cancelled reminder job {job_id}")
        return True
    except Exception as e:
        print(f"[Scheduler] Error cancelling job {job_id}: {e}")
        return False


async def send_task_reminder(task_id: str, task_title: str):
    """
    Send a reminder notification for a task.
    
    Args:
        task_id: Task ID
        task_title: Task title
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Get task details
            task = await conn.fetchrow("SELECT * FROM tasks WHERE id = $1", task_id)
            if not task:
                print(f"[Scheduler] Task {task_id} not found for reminder")
                return
            
            # Mark reminder as sent
            await conn.execute(
                """
                UPDATE tasks 
                SET reminder_sent = TRUE, reminder_sent_at = NOW()
                WHERE id = $1
                """,
                task_id,
            )
            
            # Send notification
            from app.notifications.dispatcher import send_reminder_notification
            await send_reminder_notification(
                reminder_id=f"task_{task_id}",
                user_id=str(task.get("contact_id", "unknown")),
                event_id=task_id,
                reminder_type="in_app",
                message=f"Reminder: {task_title}",
            )
            
            print(f"[Scheduler] Sent reminder for task {task_id}: {task_title}")
    except Exception as e:
        print(f"[Scheduler] Error sending task reminder: {e}")


def shutdown_scheduler():
    """Shutdown the scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        _scheduler = None
        print("[Scheduler] APScheduler shut down")

