"""Scheduler API endpoints."""
from fastapi import APIRouter, HTTPException, Depends, Body, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.db.connection import get_pool
from app.tools.scheduling_handlers import (
    parse_schedule,
    create_event,
    find_availability,
    reschedule_event,
    cancel_event,
    create_reminder,
)
from app.connectors.google_adapter import build_google_oauth_url, exchange_google_code
from app.connectors.outlook_adapter import build_outlook_oauth_url, exchange_outlook_code
from app.middleware.rbac import get_current_user
import uuid
import os

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request for scheduling assistant."""
    messages: List[Dict[str, str]]
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None


class ParseScheduleRequest(BaseModel):
    """Parse schedule request."""
    natural_language: str
    user_id: Optional[str] = None


class CreateEventRequest(BaseModel):
    """Create event request."""
    title: str
    start_time: str
    end_time: str
    calendar_provider: str = "google"
    attendees: Optional[List[str]] = None
    location: Optional[str] = None
    description: Optional[str] = None
    timezone: str = "UTC"
    recurrence_rule: Optional[str] = None


class FindAvailabilityRequest(BaseModel):
    """Find availability request."""
    start_date: str
    end_date: str
    duration_minutes: int = 60
    calendar_provider: str = "google"


class RescheduleEventRequest(BaseModel):
    """Reschedule event request."""
    new_start_time: str
    new_end_time: str


class CreateReminderRequest(BaseModel):
    """Create reminder request."""
    reminder_type: str
    minutes_before: int
    message: Optional[str] = None


@router.post("/chat")
async def scheduler_chat(
    request: ChatRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Scheduling-specialized chat endpoint with function calling.
    
    Uses LLM with scheduling tools registered in the function registry.
    Automatically detects scheduling requests and routes to appropriate tools.
    """
    """
    Scheduling-specialized chat endpoint with function calling.
    
    Uses LLM with scheduling tools registered in the function registry.
    """
    from app.tools.registry import get_registry
    from app.clients.llm import generate_chat_completion, LLMMessage, LLMRequestOptions
    
    registry = get_registry()
    tools = registry.list_schemas()
    
    # Add scheduling tools to registry if not already registered
    from app.tools.scheduling_handlers import (
        parse_schedule,
        create_event,
        find_availability,
        reschedule_event,
        cancel_event,
        create_reminder,
    )
    
    # Register scheduling tools
    if not registry.get_tool("parse_schedule"):
        registry.register_tool(
            name="parse_schedule",
            schema={
                "description": "Parse natural language scheduling request into structured format",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "natural_language": {"type": "string", "description": "User's scheduling request in natural language"},
                        "user_id": {"type": "string", "description": "User ID"},
                    },
                    "required": ["natural_language"],
                },
            },
            handler=parse_schedule,
        )
    
    if not registry.get_tool("create_event"):
        registry.register_tool(
            name="create_event",
            schema={
                "description": "Create a calendar event",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "start_time": {"type": "string", "format": "date-time"},
                        "end_time": {"type": "string", "format": "date-time"},
                        "user_id": {"type": "string"},
                        "calendar_provider": {"type": "string", "enum": ["google", "outlook"]},
                        "attendees": {"type": "array", "items": {"type": "string"}},
                        "location": {"type": "string"},
                        "description": {"type": "string"},
                        "timezone": {"type": "string"},
                        "recurrence_rule": {"type": "string"},
                    },
                    "required": ["title", "start_time", "end_time", "user_id"],
                },
            },
            handler=create_event,
        )
    
    # Call LLM with function calling enabled
    messages = [LLMMessage(msg["role"], msg["content"]) for msg in request.messages]
    
    response = await generate_chat_completion(
        LLMRequestOptions(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
    )
    
    # Handle function calls
    if response.function_call:
        function_name = response.function_call.get("name")
        function_args = response.function_call.get("arguments", {})
        
        # Add user_id to function args
        function_args["user_id"] = user_id
        
        result = await registry.call(function_name, function_args)
        
        return {
            "response": response.content,
            "function_call": {
                "name": function_name,
                "result": result,
            },
        }
    
    return {"response": response.content}


@router.post("/parse")
async def parse_schedule_endpoint(
    request: ParseScheduleRequest,
    user_id: str = Depends(get_current_user),
):
    """Parse natural language scheduling request."""
    result = await parse_schedule(
        natural_language=request.natural_language,
        user_id=user_id or request.user_id,
    )
    return result


@router.post("/create_event")
async def create_event_endpoint(
    request: CreateEventRequest,
    user_id: str = Depends(get_current_user),
):
    """Create a calendar event."""
    result = await create_event(
        title=request.title,
        start_time=request.start_time,
        end_time=request.end_time,
        user_id=user_id,
        calendar_provider=request.calendar_provider,
        attendees=request.attendees,
        location=request.location,
        description=request.description,
        timezone=request.timezone,
        recurrence_rule=request.recurrence_rule,
    )
    return result


@router.post("/find_availability")
async def find_availability_endpoint(
    request: FindAvailabilityRequest,
    user_id: str = Depends(get_current_user),
):
    """Find available time slots."""
    result = await find_availability(
        user_id=user_id,
        start_date=request.start_date,
        end_date=request.end_date,
        duration_minutes=request.duration_minutes,
        calendar_provider=request.calendar_provider,
    )
    return result


@router.post("/reschedule")
async def reschedule_event_endpoint(
    event_id: str,
    request: RescheduleEventRequest,
    user_id: str = Depends(get_current_user),
):
    """Reschedule an event."""
    result = await reschedule_event(
        event_id=event_id,
        new_start_time=request.new_start_time,
        new_end_time=request.new_end_time,
        user_id=user_id,
    )
    return result


@router.post("/cancel_event")
async def cancel_event_endpoint(
    event_id: str,
    user_id: str = Depends(get_current_user),
):
    """Cancel an event."""
    result = await cancel_event(
        event_id=event_id,
        user_id=user_id,
    )
    return result


@router.post("/connect/google")
async def connect_google(
    redirect_uri: str = Query(...),
    user_id: str = Depends(get_current_user),
):
    """Get Google OAuth URL."""
    state = str(uuid.uuid4())
    # Store state in session/DB for validation
    oauth_url = build_google_oauth_url(redirect_uri, state)
    return {"oauth_url": oauth_url, "state": state}


@router.get("/oauth2callback/google")
async def google_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    redirect_uri: str = Query(...),
    user_id: str = Depends(get_current_user),
):
    """Handle Google OAuth callback."""
    tokens = await exchange_google_code(code, redirect_uri)
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Get user's email from Google (TODO: fetch from Google API)
        # For now, use a placeholder
        email = f"{user_id}@example.com"
        
        # Store calendar connection
        await conn.execute(
            """
            INSERT INTO calendar_connections (
                id, user_id, provider, calendar_id, access_token, refresh_token,
                token_expires_at, email
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (user_id, provider) DO UPDATE SET
                access_token = EXCLUDED.access_token,
                refresh_token = EXCLUDED.refresh_token,
                token_expires_at = EXCLUDED.token_expires_at,
                updated_at = NOW()
            """,
            str(uuid.uuid4()),
            user_id,
            "google",
            "primary",  # Default calendar
            tokens["access_token"],
            tokens.get("refresh_token"),
            datetime.now().replace(second=0, microsecond=0) + timedelta(seconds=tokens.get("expires_in", 3600)),
            email,
        )
    
    return {"success": True, "provider": "google"}


@router.post("/connect/outlook")
async def connect_outlook(
    redirect_uri: str = Query(...),
    user_id: str = Depends(get_current_user),
):
    """Get Outlook OAuth URL."""
    state = str(uuid.uuid4())
    oauth_url = build_outlook_oauth_url(redirect_uri, state)
    return {"oauth_url": oauth_url, "state": state}


@router.get("/oauth2callback/outlook")
async def outlook_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    redirect_uri: str = Query(...),
    user_id: str = Depends(get_current_user),
):
    """Handle Outlook OAuth callback."""
    tokens = await exchange_outlook_code(code, redirect_uri)
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        email = f"{user_id}@example.com"
        
        await conn.execute(
            """
            INSERT INTO calendar_connections (
                id, user_id, provider, calendar_id, access_token, refresh_token,
                token_expires_at, email
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (user_id, provider) DO UPDATE SET
                access_token = EXCLUDED.access_token,
                refresh_token = EXCLUDED.refresh_token,
                token_expires_at = EXCLUDED.token_expires_at,
                updated_at = NOW()
            """,
            str(uuid.uuid4()),
            user_id,
            "outlook",
            "primary",
            tokens["access_token"],
            tokens.get("refresh_token"),
            datetime.now().replace(second=0, microsecond=0) + timedelta(seconds=tokens.get("expires_in", 3600)),
            email,
        )
    
    return {"success": True, "provider": "outlook"}


@router.get("/events")
async def list_events(
    user_id: str = Depends(get_current_user),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """List user's calendar events."""
    pool = await get_pool()
    
    query = """
        SELECT id, title, description, start_time, end_time, timezone,
               location, attendees, recurrence_rule, status, calendar_provider
        FROM event_mirror
        WHERE user_id = $1
    """
    params = [user_id]
    
    if start_date:
        query += " AND start_time >= $2"
        params.append(datetime.fromisoformat(start_date))
    if end_date:
        query += f" AND end_time <= ${len(params) + 1}"
        params.append(datetime.fromisoformat(end_date))
    
    query += " ORDER BY start_time ASC"
    
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
    
    events = []
    for row in rows:
        events.append({
            "id": str(row["id"]),
            "title": row["title"],
            "description": row.get("description"),
            "start_time": row["start_time"].isoformat() if row["start_time"] else None,
            "end_time": row["end_time"].isoformat() if row["end_time"] else None,
            "timezone": row.get("timezone"),
            "location": row.get("location"),
            "attendees": row.get("attendees", []),
            "recurrence_rule": row.get("recurrence_rule"),
            "status": row["status"],
            "calendar_provider": row["calendar_provider"],
        })
    
    return {"events": events}


@router.post("/reminders")
async def create_reminder_endpoint(
    event_id: str,
    request: CreateReminderRequest,
    user_id: str = Depends(get_current_user),
):
    """Create a reminder for an event."""
    result = await create_reminder(
        event_id=event_id,
        user_id=user_id,
        reminder_type=request.reminder_type,
        minutes_before=request.minutes_before,
        message=request.message,
    )
    return result

