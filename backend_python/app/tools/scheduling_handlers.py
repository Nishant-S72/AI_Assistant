"""Scheduling tool handlers for LLM function calling."""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import uuid
from app.connectors.calendar_api import CalendarEvent
from app.db.connection import get_pool


async def parse_schedule(
    natural_language: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parse natural language scheduling request into structured format using LLM.
    
    Args:
        natural_language: User's natural language scheduling request
        user_id: User ID (optional, for context)
    
    Returns:
        Dict with parsed schedule details: title, start_time, end_time, attendees, etc.
    """
    from app.clients.llm import generate_chat_completion, LLMMessage, LLMRequestOptions
    import os
    import re
    
    if not natural_language:
        return {
            "title": "Meeting",
            "start_time": (datetime.now() + timedelta(days=1)).isoformat(),
            "end_time": (datetime.now() + timedelta(days=1, hours=1)).isoformat(),
            "attendees": [],
            "location": None,
            "description": None,
            "timezone": "UTC",
            "recurrence_rule": None,
        }
    
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    tomorrow_date_str = tomorrow.strftime("%Y-%m-%d")
    today_date_str = now.strftime("%Y-%m-%d")
    
    system_prompt = f"""You are a helpful calendar assistant. Extract calendar event details from natural language.

CRITICAL RULES:
1. Return ONLY valid JSON - no explanations, no markdown, no code blocks
2. Start with {{ and end with }}
3. Use double quotes for all strings
4. Calculate dates relative to: {now.isoformat()}
5. Today is: {today_date_str}, Tomorrow is: {tomorrow_date_str}
6. USE SMART DEFAULTS - don't ask for clarification, just use reasonable defaults:
   - If no title: use "Meeting" or extract from context
   - If no time: use today at 2pm (14:00) or extract from context
   - If no duration: default to 1 hour
   - If no attendees mentioned: use empty array []
   - If user said "no participants" or "just me": use empty array []
   - If recurring mentioned: set is_recurring=true and recurrence_pattern (daily/weekly/monthly/yearly)

JSON Schema:
{{
  "title": "string (required - use 'Meeting' if not specified)",
  "start_time": "ISO 8601 datetime (required - use today at 2pm if not specified)",
  "end_time": "ISO 8601 datetime (required - default: 1 hour after start_time)",
  "description": "string or null",
  "is_recurring": "boolean (default: false)",
  "recurrence_pattern": "daily|weekly|monthly|yearly or null",
  "recurrence_interval": "number (default 1)",
  "location": "string or null",
  "attendees": "array of strings or [] (use [] if not mentioned or user said 'no participants')",
  "timezone": "string (default: UTC)",
  "recurrence_rule": "RRULE string or null"
}}

Examples (copy format exactly):
"Meeting tomorrow at 2pm" → {{"title":"Meeting","start_time":"{tomorrow_date_str}T14:00:00","end_time":"{tomorrow_date_str}T15:00:00","attendees":[],"timezone":"UTC"}}
"Standup every Monday 9am" → {{"title":"Standup","start_time":"2024-11-25T09:00:00","end_time":"2024-11-25T09:30:00","is_recurring":true,"recurrence_pattern":"weekly","recurrence_rule":"FREQ=WEEKLY;BYDAY=MO","attendees":[],"timezone":"UTC"}}

Return ONLY the JSON object, nothing else."""

    try:
        llm_response = await generate_chat_completion(
            LLMRequestOptions(
                model=os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL", "gpt-4o-mini"),
                messages=[
                    LLMMessage("system", system_prompt),
                    LLMMessage("user", natural_language),
                ],
                temperature=0.0,
                max_tokens=300,
                use_local=False,
            )
        )
        
        # Parse LLM response
        json_text = llm_response.content.strip()
        json_text = re.sub(r"```json\s*", "", json_text).replace("```", "")
        json_match = re.search(r"\{[\s\S]*\}", json_text)
        if json_match:
            event_data = json.loads(json_match.group(0))
        else:
            event_data = json.loads(json_text)
        
        # Ensure required fields with defaults
        if not event_data.get("title"):
            event_data["title"] = "Meeting"
        if not event_data.get("start_time"):
            default_start = now.replace(hour=14, minute=0, second=0, microsecond=0)
            event_data["start_time"] = default_start.isoformat()
        if not event_data.get("end_time"):
            start = datetime.fromisoformat(event_data["start_time"].replace("Z", "+00:00"))
            end = start + timedelta(hours=1)
            event_data["end_time"] = end.isoformat()
        if "attendees" not in event_data:
            event_data["attendees"] = []
        if "timezone" not in event_data:
            event_data["timezone"] = "UTC"
        
        return event_data
    
    except Exception as e:
        print(f"[ParseSchedule] Error parsing schedule: {e}")
        # Fallback to defaults
        return {
            "title": "Meeting",
            "start_time": (datetime.now() + timedelta(days=1)).isoformat(),
            "end_time": (datetime.now() + timedelta(days=1, hours=1)).isoformat(),
            "attendees": [],
            "location": None,
            "description": natural_language,
            "timezone": "UTC",
            "recurrence_rule": None,
        }


async def create_event(
    title: str,
    start_time: str,
    end_time: str,
    user_id: str,
    calendar_provider: str = "google",
    attendees: Optional[List[str]] = None,
    location: Optional[str] = None,
    description: Optional[str] = None,
    timezone: str = "UTC",
    recurrence_rule: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a calendar event.
    
    Args:
        title: Event title
        start_time: Start time (ISO format)
        end_time: End time (ISO format)
        user_id: User ID
        calendar_provider: Calendar provider ('google' or 'outlook')
        attendees: List of attendee emails
        location: Event location
        description: Event description
        timezone: Timezone (e.g., 'America/New_York')
        recurrence_rule: RRULE string for recurring events
    
    Returns:
        Dict with created event details
    """
    pool = await get_pool()
    
    # Get user's calendar connection
    async with pool.acquire() as conn:
        conn_row = await conn.fetchrow(
            """
            SELECT id, calendar_id, access_token, refresh_token
            FROM calendar_connections
            WHERE user_id = $1 AND provider = $2
            """,
            user_id,
            calendar_provider,
        )
        
        if not conn_row:
            raise ValueError(f"No {calendar_provider} calendar connection found for user")
        
        # Create calendar adapter
        if calendar_provider == "google":
            from app.connectors.google_adapter import GoogleCalendarAdapter
            adapter = GoogleCalendarAdapter(
                access_token=conn_row["access_token"],
                refresh_token=conn_row.get("refresh_token"),
            )
        elif calendar_provider == "outlook":
            from app.connectors.outlook_adapter import OutlookCalendarAdapter
            adapter = OutlookCalendarAdapter(
                access_token=conn_row["access_token"],
                refresh_token=conn_row.get("refresh_token"),
            )
        else:
            raise ValueError(f"Unsupported calendar provider: {calendar_provider}")
        
        # Create event in calendar
        calendar_event = CalendarEvent(
            external_id="",  # Will be set by adapter
            title=title,
            description=description,
            start_time=datetime.fromisoformat(start_time.replace("Z", "+00:00")),
            end_time=datetime.fromisoformat(end_time.replace("Z", "+00:00")),
            timezone=timezone,
            location=location,
            attendees=[{"email": email, "name": email} for email in (attendees or [])],
            recurrence_rule=recurrence_rule,
        )
        
        created_event = await adapter.create_event(
            calendar_id=conn_row["calendar_id"],
            event=calendar_event,
        )
        
        # Mirror event to local DB
        event_id = str(uuid.uuid4())
        await conn.execute(
            """
            INSERT INTO event_mirror (
                id, user_id, external_event_id, calendar_provider, calendar_id,
                title, description, start_time, end_time, timezone, location,
                attendees, recurrence_rule, status
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
            event_id,
            user_id,
            created_event.external_id,
            calendar_provider,
            conn_row["calendar_id"],
            title,
            description,
            created_event.start_time,
            created_event.end_time,
            timezone,
            location,
            json.dumps(created_event.attendees),
            recurrence_rule,
            "confirmed",
        )
        
        # Schedule reminders (if needed)
        from app.scheduler.apscheduler_manager import schedule_reminders_for_event
        await schedule_reminders_for_event(event_id, user_id, created_event.start_time)
        
        return {
            "success": True,
            "event_id": event_id,
            "external_event_id": created_event.external_id,
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
        }


async def find_availability(
    user_id: str,
    start_date: str,
    end_date: str,
    duration_minutes: int = 60,
    calendar_provider: str = "google",
) -> Dict[str, Any]:
    """
    Find available time slots.
    
    Args:
        user_id: User ID
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
        duration_minutes: Duration in minutes
        calendar_provider: Calendar provider
    
    Returns:
        Dict with available time slots
    """
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        conn_row = await conn.fetchrow(
            """
            SELECT id, calendar_id, access_token, refresh_token
            FROM calendar_connections
            WHERE user_id = $1 AND provider = $2
            """,
            user_id,
            calendar_provider,
        )
        
        if not conn_row:
            raise ValueError(f"No {calendar_provider} calendar connection found")
        
        # Get free/busy information
        if calendar_provider == "google":
            from app.connectors.google_adapter import GoogleCalendarAdapter
            adapter = GoogleCalendarAdapter(
                access_token=conn_row["access_token"],
                refresh_token=conn_row.get("refresh_token"),
            )
        elif calendar_provider == "outlook":
            from app.connectors.outlook_adapter import OutlookCalendarAdapter
            adapter = OutlookCalendarAdapter(
                access_token=conn_row["access_token"],
                refresh_token=conn_row.get("refresh_token"),
            )
        else:
            raise ValueError(f"Unsupported calendar provider: {calendar_provider}")
        
        time_min = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        time_max = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        
        freebusy = await adapter.get_freebusy(
            calendar_id=conn_row["calendar_id"],
            time_min=time_min,
            time_max=time_max,
        )
        
        # Find available slots
        available_slots = []
        current = time_min
        while current < time_max:
            slot_end = current + timedelta(minutes=duration_minutes)
            # Check if this slot is free
            is_busy = any(
                slot.busy and slot.start <= current < slot.end
                for slot in freebusy
            )
            if not is_busy:
                available_slots.append({
                    "start": current.isoformat(),
                    "end": slot_end.isoformat(),
                })
            current += timedelta(minutes=30)  # Check every 30 minutes
        
        return {
            "available_slots": available_slots[:10],  # Return top 10
            "duration_minutes": duration_minutes,
        }


async def reschedule_event(
    event_id: str,
    new_start_time: str,
    new_end_time: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    Reschedule an existing event.
    
    Args:
        event_id: Event ID (from event_mirror)
        new_start_time: New start time (ISO format)
        new_end_time: New end time (ISO format)
        user_id: User ID
    
    Returns:
        Dict with updated event details
    """
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Get event from mirror
        event_row = await conn.fetchrow(
            """
            SELECT external_event_id, calendar_provider, calendar_id
            FROM event_mirror
            WHERE id = $1 AND user_id = $2
            """,
            event_id,
            user_id,
        )
        
        if not event_row:
            raise ValueError("Event not found")
        
        # Get calendar connection
        conn_row = await conn.fetchrow(
            """
            SELECT access_token, refresh_token
            FROM calendar_connections
            WHERE user_id = $1 AND provider = $2
            """,
            user_id,
            event_row["calendar_provider"],
        )
        
        if not conn_row:
            raise ValueError("Calendar connection not found")
        
        # Update event in calendar
        if event_row["calendar_provider"] == "google":
            from app.connectors.google_adapter import GoogleCalendarAdapter
            adapter = GoogleCalendarAdapter(
                access_token=conn_row["access_token"],
                refresh_token=conn_row.get("refresh_token"),
            )
        elif event_row["calendar_provider"] == "outlook":
            from app.connectors.outlook_adapter import OutlookCalendarAdapter
            adapter = OutlookCalendarAdapter(
                access_token=conn_row["access_token"],
                refresh_token=conn_row.get("refresh_token"),
            )
        else:
            raise ValueError(f"Unsupported provider: {event_row['calendar_provider']}")
        
        updated_event = CalendarEvent(
            external_id=event_row["external_event_id"],
            title="",  # Will be fetched from existing event
            start_time=datetime.fromisoformat(new_start_time.replace("Z", "+00:00")),
            end_time=datetime.fromisoformat(new_end_time.replace("Z", "+00:00")),
        )
        
        await adapter.update_event(
            calendar_id=event_row["calendar_id"],
            event_id=event_row["external_event_id"],
            event=updated_event,
        )
        
        # Update mirror
        await conn.execute(
            """
            UPDATE event_mirror
            SET start_time = $1, end_time = $2, updated_at = NOW()
            WHERE id = $3
            """,
            updated_event.start_time,
            updated_event.end_time,
            event_id,
        )
        
        return {
            "success": True,
            "event_id": event_id,
            "new_start_time": new_start_time,
            "new_end_time": new_end_time,
        }


async def cancel_event(
    event_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    Cancel an event.
    
    Args:
        event_id: Event ID (from event_mirror)
        user_id: User ID
    
    Returns:
        Dict with cancellation status
    """
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Get event from mirror
        event_row = await conn.fetchrow(
            """
            SELECT external_event_id, calendar_provider, calendar_id
            FROM event_mirror
            WHERE id = $1 AND user_id = $2
            """,
            event_id,
            user_id,
        )
        
        if not event_row:
            raise ValueError("Event not found")
        
        # Get calendar connection
        conn_row = await conn.fetchrow(
            """
            SELECT access_token, refresh_token
            FROM calendar_connections
            WHERE user_id = $1 AND provider = $2
            """,
            user_id,
            event_row["calendar_provider"],
        )
        
        if not conn_row:
            raise ValueError("Calendar connection not found")
        
        # Delete event from calendar
        if event_row["calendar_provider"] == "google":
            from app.connectors.google_adapter import GoogleCalendarAdapter
            adapter = GoogleCalendarAdapter(
                access_token=conn_row["access_token"],
                refresh_token=conn_row.get("refresh_token"),
            )
        elif event_row["calendar_provider"] == "outlook":
            from app.connectors.outlook_adapter import OutlookCalendarAdapter
            adapter = OutlookCalendarAdapter(
                access_token=conn_row["access_token"],
                refresh_token=conn_row.get("refresh_token"),
            )
        else:
            raise ValueError(f"Unsupported provider: {event_row['calendar_provider']}")
        
        await adapter.delete_event(
            calendar_id=event_row["calendar_id"],
            event_id=event_row["external_event_id"],
        )
        
        # Update mirror status
        await conn.execute(
            """
            UPDATE event_mirror
            SET status = 'cancelled', updated_at = NOW()
            WHERE id = $1
            """,
            event_id,
        )
        
        # Cancel associated reminders
        await conn.execute(
            """
            UPDATE reminders
            SET status = 'cancelled', updated_at = NOW()
            WHERE event_id = $1
            """,
            event_id,
        )
        
        return {
            "success": True,
            "event_id": event_id,
        }


async def create_reminder(
    event_id: str,
    user_id: str,
    reminder_type: str,
    minutes_before: int,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a reminder for an event.
    
    Args:
        event_id: Event ID
        user_id: User ID
        reminder_type: Type of reminder ('email', 'slack', 'in_app')
        minutes_before: Minutes before event to trigger reminder
        message: Custom reminder message
    
    Returns:
        Dict with reminder details
    """
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Get event
        event_row = await conn.fetchrow(
            """
            SELECT start_time
            FROM event_mirror
            WHERE id = $1 AND user_id = $2
            """,
            event_id,
            user_id,
        )
        
        if not event_row:
            raise ValueError("Event not found")
        
        trigger_time = event_row["start_time"] - timedelta(minutes=minutes_before)
        
        reminder_id = str(uuid.uuid4())
        await conn.execute(
            """
            INSERT INTO reminders (
                id, user_id, event_id, reminder_type, trigger_time, message, status
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            reminder_id,
            user_id,
            event_id,
            reminder_type,
            trigger_time,
            message,
            "pending",
        )
        
        # Schedule reminder in APScheduler
        from app.scheduler.apscheduler_manager import schedule_reminder
        job_id = await schedule_reminder(reminder_id, trigger_time, user_id, event_id, reminder_type, message)
        
        # Update reminder with job ID
        await conn.execute(
            """
            UPDATE reminders
            SET apscheduler_job_id = $1
            WHERE id = $2
            """,
            job_id,
            reminder_id,
        )
        
        return {
            "success": True,
            "reminder_id": reminder_id,
            "trigger_time": trigger_time.isoformat(),
        }


