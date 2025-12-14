"""
Calendar API endpoints for standalone event and reminder management.

This module provides full CRUD operations for calendar events and reminders,
with optional Google Calendar integration.
"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Header
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from app.db.connection import get_pool
from app.connectors.google_adapter import GoogleCalendarAdapter
from app.scheduler.apscheduler_manager import get_scheduler
import json
import os
import uuid


router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])


# Pydantic models for request/response
class Attendee(BaseModel):
    email: str
    name: Optional[str] = None
    status: Optional[str] = "needsAction"  # needsAction, accepted, declined, tentative


class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    location: Optional[str] = None
    video_link: Optional[str] = None
    start: str  # ISO 8601 datetime
    end: str  # ISO 8601 datetime
    all_day: bool = False
    color: Optional[str] = Field(default="#4285F4", pattern=r"^#[0-9A-Fa-f]{6}$|^[a-z]+$")
    timezone: Optional[str] = "UTC"
    recurrence_rule: Optional[str] = None  # RRULE format
    attendees: Optional[List[Attendee]] = []
    sync_to_google: bool = False  # If True and Google connected, sync to Google


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    location: Optional[str] = None
    video_link: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    all_day: Optional[bool] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$|^[a-z]+$")
    timezone: Optional[str] = None
    recurrence_rule: Optional[str] = None
    attendees: Optional[List[Attendee]] = None
    sync_to_google: Optional[bool] = False


class ReminderCreate(BaseModel):
    minutes_before: Optional[int] = None  # Relative reminder
    when: Optional[str] = None  # Absolute reminder (ISO 8601)
    channel: str = Field(default="inapp", pattern="^(inapp|email|slack)$")
    repeat_rule: Optional[str] = None


class EventResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: Optional[str]
    location: Optional[str]
    video_link: Optional[str]
    start: str
    end: str
    all_day: bool
    color: str
    timezone: str
    recurrence_rule: Optional[str]
    attendees: List[Dict[str, Any]]
    source: str
    source_event_id: Optional[str]
    created_at: str
    updated_at: str


class ReminderResponse(BaseModel):
    id: str
    user_id: str
    event_id: Optional[str]
    minutes_before: Optional[int]
    when: Optional[str]
    channel: str
    repeat_rule: Optional[str]
    delivered: bool
    created_at: str
    updated_at: str


# Helper function to get current user (simplified - replace with actual auth)
async def get_current_user(x_user_id: Optional[str] = Header(None, alias="X-User-ID")) -> str:
    """Get current user ID from header or default to demo user."""
    if x_user_id:
        return x_user_id
    # Default to demo user for development
    return os.getenv("DEFAULT_USER_ID", "00000000-0000-0000-0000-000000000000")


# Helper function to check if Google is connected for a user
async def get_google_connection(user_id: str) -> Optional[Dict[str, Any]]:
    """Get Google calendar connection for user if exists."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM calendar_connections 
            WHERE user_id = $1 AND provider = 'google'
            """,
            user_id,
        )
        if row:
            return dict(row)
    return None


# Helper function to schedule reminder
async def schedule_reminder(reminder_id: str, user_id: str, event_id: str, trigger_time: datetime, channel: str, message: str):
    """Schedule a reminder using APScheduler."""
    scheduler = get_scheduler()
    if not scheduler:
        print(f"[Calendar] APScheduler not available, reminder {reminder_id} not scheduled")
        return
    
    job_id = f"reminder_{reminder_id}"
    
    # Import here to avoid circular imports
    from app.scheduler.apscheduler_manager import send_reminder_notification
    
    scheduler.add_job(
        send_reminder_notification,
        'date',
        run_date=trigger_time,
        args=[reminder_id, user_id, event_id, channel, message],
        id=job_id,
        replace_existing=True,
    )
    
    # Update reminder with job ID
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE reminders SET apscheduler_job_id = $1, updated_at = NOW()
            WHERE id = $2
            """,
            job_id,
            reminder_id,
        )


@router.get("/events", response_model=Dict[str, List[EventResponse]])
async def list_events(
    start: str = Query(..., description="Start date (ISO 8601)"),
    end: str = Query(..., description="End date (ISO 8601)"),
    source: Optional[str] = Query(None, description="Filter by source: 'local' or 'google'"),
    user_id: str = Depends(get_current_user),
):
    """
    List events in a date range.
    
    Returns both local events and optionally synced Google events.
    """
    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            query = """
                SELECT * FROM events 
                WHERE user_id = $1 
                AND start >= $2 
                AND "end" <= $3
            """
            params = [user_id, start_dt, end_dt]
            
            if source:
                query += " AND source = $4"
                params.append(source)
            
            query += " ORDER BY start ASC"
            
            rows = await conn.fetch(query, *params)
        
        events = []
        for row in rows:
            event_dict = dict(row)
            # Parse attendees JSON
            if isinstance(event_dict.get("attendees_json"), str):
                event_dict["attendees"] = json.loads(event_dict["attendees_json"])
            elif isinstance(event_dict.get("attendees_json"), (list, dict)):
                event_dict["attendees"] = event_dict["attendees_json"]
            else:
                event_dict["attendees"] = []
            
            # Convert datetime to ISO strings
            for field in ["start", "end", "created_at", "updated_at"]:
                if isinstance(event_dict.get(field), datetime):
                    event_dict[field] = event_dict[field].isoformat()
            
            events.append(EventResponse(**event_dict))
        
        return {"events": events}
    except Exception as error:
        print(f"[Calendar] Error listing events: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to list events: {str(error)}")


@router.post("/events", response_model=EventResponse)
async def create_event(
    event: EventCreate,
    user_id: str = Depends(get_current_user),
):
    """
    Create a new calendar event.
    
    If sync_to_google=True and user has Google connected, also creates the event in Google Calendar.
    """
    try:
        # Validate dates
        start_dt = datetime.fromisoformat(event.start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(event.end.replace("Z", "+00:00"))
        
        if end_dt <= start_dt:
            raise HTTPException(status_code=400, detail="End time must be after start time")
        
        # Prepare attendees JSON
        attendees_json = [a.dict() for a in event.attendees] if event.attendees else []
        
        source = "local"
        source_event_id = None
        
        # If sync_to_google and Google is connected, create in Google
        if event.sync_to_google:
            google_conn = await get_google_connection(user_id)
            if google_conn:
                try:
                    adapter = GoogleCalendarAdapter(
                        access_token=google_conn["access_token"],
                        refresh_token=google_conn.get("refresh_token"),
                    )
                    
                    from app.connectors.calendar_api import CalendarEvent
                    google_event = CalendarEvent(
                        external_id="",  # Will be set by Google
                        title=event.title,
                        description=event.description,
                        start_time=start_dt,
                        end_time=end_dt,
                        timezone=event.timezone or "UTC",
                        location=event.location,
                        attendees=[{"email": a.email, "name": a.name} for a in event.attendees],
                        recurrence_rule=event.recurrence_rule,
                    )
                    
                    created_google_event = await adapter.create_event(
                        calendar_id=google_conn["calendar_id"],
                        event=google_event,
                    )
                    source = "google"
                    source_event_id = created_google_event.external_id
                except Exception as e:
                    print(f"[Calendar] Failed to sync to Google: {e}")
                    # Continue with local creation
        
        # Create local event
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO events 
                (user_id, title, description, location, video_link, start, "end", 
                 all_day, color, timezone, recurrence_rule, attendees_json, source, source_event_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                RETURNING *
                """,
                user_id,
                event.title,
                event.description,
                event.location,
                event.video_link,
                start_dt,
                end_dt,
                event.all_day,
                event.color,
                event.timezone or "UTC",
                event.recurrence_rule,
                json.dumps(attendees_json),
                source,
                source_event_id,
            )
        
        event_dict = dict(row)
        event_dict["attendees"] = attendees_json
        for field in ["start", "end", "created_at", "updated_at"]:
            if isinstance(event_dict.get(field), datetime):
                event_dict[field] = event_dict[field].isoformat()
        
        return EventResponse(**event_dict)
    except HTTPException:
        raise
    except Exception as error:
        print(f"[Calendar] Error creating event: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to create event: {str(error)}")


@router.patch("/events/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str,
    updates: EventUpdate,
    user_id: str = Depends(get_current_user),
):
    """
    Update an existing event.
    
    If event source is 'google' and sync_to_google=True, also updates Google event.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Get existing event
            existing = await conn.fetchrow(
                "SELECT * FROM events WHERE id = $1 AND user_id = $2",
                event_id,
                user_id,
            )
            
            if not existing:
                raise HTTPException(status_code=404, detail="Event not found")
            
            existing_dict = dict(existing)
            
            # Build update query
            update_fields = []
            values = []
            param_idx = 1
            
            if updates.title is not None:
                update_fields.append(f"title = ${param_idx}")
                values.append(updates.title)
                param_idx += 1
            
            if updates.description is not None:
                update_fields.append(f"description = ${param_idx}")
                values.append(updates.description)
                param_idx += 1
            
            if updates.location is not None:
                update_fields.append(f"location = ${param_idx}")
                values.append(updates.location)
                param_idx += 1
            
            if updates.video_link is not None:
                update_fields.append(f"video_link = ${param_idx}")
                values.append(updates.video_link)
                param_idx += 1
            
            if updates.start is not None:
                start_dt = datetime.fromisoformat(updates.start.replace("Z", "+00:00"))
                update_fields.append(f"start = ${param_idx}")
                values.append(start_dt)
                param_idx += 1
            else:
                start_dt = existing_dict["start"]
            
            if updates.end is not None:
                end_dt = datetime.fromisoformat(updates.end.replace("Z", "+00:00"))
                update_fields.append(f'"end" = ${param_idx}')
                values.append(end_dt)
                param_idx += 1
            else:
                end_dt = existing_dict["end"]
            
            if updates.all_day is not None:
                update_fields.append(f"all_day = ${param_idx}")
                values.append(updates.all_day)
                param_idx += 1
            
            if updates.color is not None:
                update_fields.append(f"color = ${param_idx}")
                values.append(updates.color)
                param_idx += 1
            
            if updates.timezone is not None:
                update_fields.append(f"timezone = ${param_idx}")
                values.append(updates.timezone)
                param_idx += 1
            
            if updates.recurrence_rule is not None:
                update_fields.append(f"recurrence_rule = ${param_idx}")
                values.append(updates.recurrence_rule)
                param_idx += 1
            
            if updates.attendees is not None:
                attendees_json = [a.dict() for a in updates.attendees]
                update_fields.append(f"attendees_json = ${param_idx}")
                values.append(json.dumps(attendees_json))
                param_idx += 1
            
            if updates.sync_to_google and existing_dict["source"] == "google" and existing_dict.get("source_event_id"):
                # Update Google event
                google_conn = await get_google_connection(user_id)
                if google_conn:
                    try:
                        adapter = GoogleCalendarAdapter(
                            access_token=google_conn["access_token"],
                            refresh_token=google_conn.get("refresh_token"),
                        )
                        
                        from app.connectors.calendar_api import CalendarEvent
                        google_event = CalendarEvent(
                            external_id=existing_dict["source_event_id"],
                            title=updates.title or existing_dict["title"],
                            description=updates.description if updates.description is not None else existing_dict.get("description"),
                            start_time=start_dt,
                            end_time=end_dt,
                            timezone=updates.timezone or existing_dict.get("timezone", "UTC"),
                            location=updates.location if updates.location is not None else existing_dict.get("location"),
                            attendees=[{"email": a.email, "name": a.name} for a in (updates.attendees or [])],
                            recurrence_rule=updates.recurrence_rule if updates.recurrence_rule is not None else existing_dict.get("recurrence_rule"),
                        )
                        
                        await adapter.update_event(
                            calendar_id=google_conn["calendar_id"],
                            event_id=existing_dict["source_event_id"],
                            event=google_event,
                        )
                    except Exception as e:
                        print(f"[Calendar] Failed to update Google event: {e}")
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            update_fields.append("updated_at = NOW()")
            values.extend([event_id, user_id])
            
            query = f"""
                UPDATE events 
                SET {', '.join(update_fields)}
                WHERE id = ${param_idx} AND user_id = ${param_idx + 1}
                RETURNING *
            """
            
            row = await conn.fetchrow(query, *values)
        
        event_dict = dict(row)
        if isinstance(event_dict.get("attendees_json"), str):
            event_dict["attendees"] = json.loads(event_dict["attendees_json"])
        else:
            event_dict["attendees"] = event_dict.get("attendees_json", [])
        
        for field in ["start", "end", "created_at", "updated_at"]:
            if isinstance(event_dict.get(field), datetime):
                event_dict[field] = event_dict[field].isoformat()
        
        return EventResponse(**event_dict)
    except HTTPException:
        raise
    except Exception as error:
        print(f"[Calendar] Error updating event: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to update event: {str(error)}")


@router.delete("/events/{event_id}")
async def delete_event(
    event_id: str,
    sync_to_google: bool = Query(False, description="Also delete from Google if synced"),
    user_id: str = Depends(get_current_user),
):
    """
    Delete an event.
    
    If sync_to_google=True and event source is 'google', also deletes from Google.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Get event to check source
            existing = await conn.fetchrow(
                "SELECT * FROM events WHERE id = $1 AND user_id = $2",
                event_id,
                user_id,
            )
            
            if not existing:
                raise HTTPException(status_code=404, detail="Event not found")
            
            existing_dict = dict(existing)
            
            # Delete from Google if needed
            if sync_to_google and existing_dict["source"] == "google" and existing_dict.get("source_event_id"):
                google_conn = await get_google_connection(user_id)
                if google_conn:
                    try:
                        adapter = GoogleCalendarAdapter(
                            access_token=google_conn["access_token"],
                            refresh_token=google_conn.get("refresh_token"),
                        )
                        await adapter.delete_event(
                            calendar_id=google_conn["calendar_id"],
                            event_id=existing_dict["source_event_id"],
                        )
                    except Exception as e:
                        print(f"[Calendar] Failed to delete Google event: {e}")
            
            # Delete local event (cascade will delete reminders)
            await conn.execute(
                "DELETE FROM events WHERE id = $1 AND user_id = $2",
                event_id,
                user_id,
            )
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as error:
        print(f"[Calendar] Error deleting event: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to delete event: {str(error)}")


@router.post("/events/{event_id}/reminders", response_model=ReminderResponse)
async def create_reminder(
    event_id: str,
    reminder: ReminderCreate,
    user_id: str = Depends(get_current_user),
):
    """
    Add one or more reminders to an event.
    
    Supports both relative (minutes_before) and absolute (when) reminders.
    """
    try:
        # Validate that event exists and belongs to user
        pool = await get_pool()
        async with pool.acquire() as conn:
            event = await conn.fetchrow(
                "SELECT * FROM events WHERE id = $1 AND user_id = $2",
                event_id,
                user_id,
            )
            
            if not event:
                raise HTTPException(status_code=404, detail="Event not found")
            
            event_dict = dict(event)
            
            # Calculate trigger time
            if reminder.minutes_before is not None:
                # Relative reminder
                event_start = event_dict["start"]
                if isinstance(event_start, str):
                    event_start = datetime.fromisoformat(event_start.replace("Z", "+00:00"))
                trigger_time = event_start - timedelta(minutes=reminder.minutes_before)
                when = None
            elif reminder.when:
                # Absolute reminder
                trigger_time = datetime.fromisoformat(reminder.when.replace("Z", "+00:00"))
                when = trigger_time
                reminder.minutes_before = None
            else:
                raise HTTPException(status_code=400, detail="Either minutes_before or when must be provided")
            
            # Create reminder
            row = await conn.fetchrow(
                """
                INSERT INTO reminders 
                (user_id, event_id, minutes_before, "when", channel, repeat_rule)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
                """,
                user_id,
                event_id,
                reminder.minutes_before,
                when,
                reminder.channel,
                reminder.repeat_rule,
            )
            
            reminder_dict = dict(row)
            
            # Schedule reminder job
            await schedule_reminder(
                reminder_id=str(reminder_dict["id"]),
                user_id=user_id,
                event_id=event_id,
                trigger_time=trigger_time,
                channel=reminder.channel,
                message=f"Reminder: {event_dict['title']}",
            )
            
            for field in ["when", "created_at", "updated_at"]:
                if isinstance(reminder_dict.get(field), datetime):
                    reminder_dict[field] = reminder_dict[field].isoformat()
            
            return ReminderResponse(**reminder_dict)
    except HTTPException:
        raise
    except Exception as error:
        print(f"[Calendar] Error creating reminder: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to create reminder: {str(error)}")


@router.get("/reminders", response_model=Dict[str, List[ReminderResponse]])
async def list_reminders(
    event_id: Optional[str] = Query(None, description="Filter by event ID"),
    user_id: str = Depends(get_current_user),
):
    """List reminders for a user, optionally filtered by event."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            if event_id:
                rows = await conn.fetch(
                    "SELECT * FROM reminders WHERE user_id = $1 AND event_id = $2 ORDER BY created_at DESC",
                    user_id,
                    event_id,
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM reminders WHERE user_id = $1 ORDER BY created_at DESC",
                    user_id,
                )
        
        reminders = []
        for row in rows:
            reminder_dict = dict(row)
            for field in ["when", "created_at", "updated_at"]:
                if isinstance(reminder_dict.get(field), datetime):
                    reminder_dict[field] = reminder_dict[field].isoformat()
            reminders.append(ReminderResponse(**reminder_dict))
        
        return {"reminders": reminders}
    except Exception as error:
        print(f"[Calendar] Error listing reminders: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to list reminders: {str(error)}")


@router.post("/import/google")
async def import_google_events(
    start: str = Query(..., description="Start date (ISO 8601)"),
    end: str = Query(..., description="End date (ISO 8601)"),
    user_id: str = Depends(get_current_user),
):
    """
    Import events from Google Calendar into local events.
    
    Fetches Google events in the specified range and creates/updates local events.
    """
    try:
        google_conn = await get_google_connection(user_id)
        if not google_conn:
            raise HTTPException(status_code=400, detail="Google Calendar not connected")
        
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        
        adapter = GoogleCalendarAdapter(
            access_token=google_conn["access_token"],
            refresh_token=google_conn.get("refresh_token"),
        )
        
        # Fetch events from Google
        google_events = await adapter.list_events(
            calendar_id=google_conn["calendar_id"],
            time_min=start_dt,
            time_max=end_dt,
        )
        
        imported_count = 0
        updated_count = 0
        skipped_count = 0
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            for google_event in google_events:
                # Check if event already exists
                existing = await conn.fetchrow(
                    """
                    SELECT * FROM events 
                    WHERE user_id = $1 AND source = 'google' AND source_event_id = $2
                    """,
                    user_id,
                    google_event.external_id,
                )
                
                # Convert Google event to local format
                attendees_json = google_event.attendees or []
                
                if existing:
                    # Update existing event
                    await conn.execute(
                        """
                        UPDATE events SET
                            title = $1,
                            description = $2,
                            location = $3,
                            start = $4,
                            "end" = $5,
                            timezone = $6,
                            recurrence_rule = $7,
                            attendees_json = $8,
                            updated_at = NOW()
                        WHERE id = $9
                        """,
                        google_event.title,
                        google_event.description,
                        google_event.location,
                        google_event.start_time,
                        google_event.end_time,
                        google_event.timezone or "UTC",
                        google_event.recurrence_rule,
                        json.dumps(attendees_json),
                        existing["id"],
                    )
                    updated_count += 1
                else:
                    # Create new event
                    await conn.execute(
                        """
                        INSERT INTO events 
                        (user_id, title, description, location, start, "end", timezone, 
                         recurrence_rule, attendees_json, source, source_event_id)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'google', $10)
                        """,
                        user_id,
                        google_event.title,
                        google_event.description,
                        google_event.location,
                        google_event.start_time,
                        google_event.end_time,
                        google_event.timezone or "UTC",
                        google_event.recurrence_rule,
                        json.dumps(attendees_json),
                        google_event.external_id,
                    )
                    imported_count += 1
        
        return {
            "success": True,
            "imported": imported_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "total": len(google_events),
        }
    except HTTPException:
        raise
    except Exception as error:
        print(f"[Calendar] Error importing Google events: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to import events: {str(error)}")

