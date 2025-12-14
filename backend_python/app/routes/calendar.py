"""
Legacy calendar routes - DEPRECATED.

NOTE: This module contains the old chat-bubble scheduler implementation.
Calendar scheduling has been moved to the new scheduler at /api/v1/scheduler.

These routes are kept for backward compatibility but are deprecated.
New code should use:
- /api/v1/scheduler/chat - For natural language scheduling
- /api/v1/scheduler/create_event - For direct event creation
- /api/v1/scheduler/events - For listing events from event_mirror

Migration guide:
- Old: POST /api/calendar/parse -> New: POST /api/v1/scheduler/parse
- Old: POST /api/calendar/events -> New: POST /api/v1/scheduler/create_event
- Old: GET /api/calendar/events -> New: GET /api/v1/scheduler/events
"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
from pathlib import Path
from app.db.connection import get_pool
from app.clients.llm import generate_chat_completion, LLMMessage, LLMRequestOptions
import json
import os
import re
import warnings


class CreateEventRequest(BaseModel):
    """Request model for creating a calendar event."""
    suggestionId: Optional[str] = None
    title: str
    description: Optional[str] = None
    start: str  # ISO string
    end: str  # ISO string
    attendees: Optional[List[str]] = None
    timezone: Optional[str] = None


class ParseEventRequest(BaseModel):
    """Request model for parsing calendar event from text."""
    text: str

router = APIRouter()


def generate_recurring_instances(event: Dict, start_date: datetime, end_date: datetime) -> List[Dict]:
    """Generate instances of recurring events."""
    instances = []
    pattern = event.get("recurrence_pattern")
    interval = event.get("recurrence_interval", 1)
    recurrence_end = event.get("recurrence_end_date")
    event_start = datetime.fromisoformat(event["start_time"].replace("Z", "+00:00"))
    event_end = datetime.fromisoformat(event["end_time"].replace("Z", "+00:00"))
    duration = event_end - event_start

    current = event_start
    while current <= end_date:
        if current >= start_date:
            if recurrence_end and current > datetime.fromisoformat(recurrence_end.replace("Z", "+00:00")):
                break

            instance = dict(event)
            instance["start_time"] = current.isoformat()
            instance["end_time"] = (current + duration).isoformat()
            instance["id"] = f"{event['id']}_{current.isoformat()}"
            instances.append(instance)

        if pattern == "daily":
            current += timedelta(days=interval)
        elif pattern == "weekly":
            current += timedelta(weeks=interval)
        elif pattern == "monthly":
            # Proper monthly increment with year adjustment
            new_month = current.month + interval
            new_year = current.year
            while new_month > 12:
                new_month -= 12
                new_year += 1
            current = current.replace(year=new_year, month=new_month)
        elif pattern == "yearly":
            current = current.replace(year=current.year + interval)
        else:
            break

    return instances


@router.get("/events")
async def get_events(start: str = Query(...), end: str = Query(...)):
    """
    Get events for a date range - DEPRECATED.
    
    This endpoint is deprecated. Use GET /api/v1/scheduler/events instead.
    """
    warnings.warn(
        "GET /api/calendar/events is deprecated. Use GET /api/v1/scheduler/events instead.",
        DeprecationWarning,
        stacklevel=2
    )
    try:
        # Parse dates and ensure they're timezone-aware
        start_str = start.replace("Z", "+00:00")
        end_str = end.replace("Z", "+00:00")
        
        # Handle both timezone-aware and naive datetime strings
        if "+" in start_str or start_str.endswith("Z"):
            start_date = datetime.fromisoformat(start_str)
        else:
            # If naive, assume UTC
            start_date = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        
        if "+" in end_str or end_str.endswith("Z"):
            end_date = datetime.fromisoformat(end_str)
        else:
            # If naive, assume UTC
            end_date = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        
        # Ensure both are timezone-aware (UTC)
        from datetime import timezone
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        pool = await get_pool()
        async with pool.acquire() as conn:
            # Convert timezone-aware datetimes to UTC timestamps for comparison
            # This avoids timezone comparison issues
            start_ts = start_date.timestamp() if start_date.tzinfo else start_date.replace(tzinfo=timezone.utc).timestamp()
            end_ts = end_date.timestamp() if end_date.tzinfo else end_date.replace(tzinfo=timezone.utc).timestamp()
            
            # Fetch events - compare timestamps to avoid timezone issues
            rows = await conn.fetch(
                """
                SELECT * FROM calendar_events 
                WHERE (
                    EXTRACT(EPOCH FROM start_time) >= $1 
                    AND EXTRACT(EPOCH FROM start_time) <= $2
                )
                OR (
                    is_recurring = true 
                    AND recurrence_end_date IS NOT NULL
                    AND EXTRACT(EPOCH FROM recurrence_end_date) >= $1
                )
                ORDER BY start_time ASC
                """,
                start_ts,
                end_ts,
            )

        # Expand recurring events
        events = []
        for row in rows:
            event = dict(row)
            # Convert datetime objects to ISO strings for JSON serialization
            if isinstance(event.get("start_time"), datetime):
                event["start_time"] = event["start_time"].isoformat()
            if isinstance(event.get("end_time"), datetime):
                event["end_time"] = event["end_time"].isoformat()
            if isinstance(event.get("created_at"), datetime):
                event["created_at"] = event["created_at"].isoformat()
            if isinstance(event.get("updated_at"), datetime):
                event["updated_at"] = event["updated_at"].isoformat()
            if isinstance(event.get("recurrence_end_date"), datetime):
                event["recurrence_end_date"] = event["recurrence_end_date"].isoformat()
            
            if event.get("is_recurring") and event.get("recurrence_pattern"):
                instances = generate_recurring_instances(event, start_date, end_date)
                events.extend(instances)
            else:
                events.append(event)

        # Sort events by start_time (handle both string and datetime)
        def get_start_time(e):
            start = e.get("start_time")
            if isinstance(start, str):
                return datetime.fromisoformat(start.replace("Z", "+00:00"))
            return start
        
        events.sort(key=get_start_time)
        return {"events": events}
    except Exception as error:
        print(f"Error fetching calendar events: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch calendar events: {str(error)}")


@router.post("/events")
async def create_event(request: CreateEventRequest):
    """
    Create a new calendar event - DEPRECATED.
    
    This endpoint is deprecated. Use POST /api/v1/scheduler/create_event instead.
    """
    warnings.warn(
        "POST /api/calendar/events is deprecated. Use POST /api/v1/scheduler/create_event instead.",
        DeprecationWarning,
        stacklevel=2
    )
    try:
        if not request.title or not request.start or not request.end:
            raise HTTPException(status_code=400, detail="Title, start, and end are required")
        
        # Validate times
        try:
            start_dt = datetime.fromisoformat(request.start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(request.end.replace("Z", "+00:00"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
        
        if end_dt <= start_dt:
            raise HTTPException(status_code=400, detail="End time must be after start time")
        
        event_source = "simulated"
        google_event_id = None
        
        # Try Google Calendar if configured
        google_oauth_token = os.getenv("GOOGLE_OAUTH_TOKEN")
        if google_oauth_token:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # Create Google Calendar event
                    google_response = await client.post(
                        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                        headers={
                            "Authorization": f"Bearer {google_oauth_token}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "summary": request.title,
                            "description": request.description or "",
                            "start": {
                                "dateTime": request.start,
                                "timeZone": request.timezone or "UTC",
                            },
                            "end": {
                                "dateTime": request.end,
                                "timeZone": request.timezone or "UTC",
                            },
                            "attendees": [{"email": email} for email in (request.attendees or [])],
                        },
                    )
                    
                    if google_response.status_code == 200:
                        google_data = google_response.json()
                        google_event_id = google_data.get("id")
                        event_source = "google"
            except Exception as e:
                print(f"[Calendar] Google Calendar creation failed: {e}")
                # Fallback to simulated
        
        # Save to database
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO calendar_events 
                (title, description, start_time, end_time, location, attendees)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
                """,
                request.title,
                request.description,
                start_dt,
                end_dt,
                None,  # location
                json.dumps(request.attendees or []),
            )
            
            # Save simulated event to JSON if not using DB
            if event_source == "simulated":
                storage_path = Path(__file__).parent.parent.parent.parent / "backend" / "storage" / "simulated_events.json"
                if not storage_path.exists():
                    storage_path = Path.cwd() / "backend_python" / "storage" / "simulated_events.json"
                    storage_path.parent.mkdir(parents=True, exist_ok=True)
                
                simulated_events = []
                if storage_path.exists():
                    try:
                        with open(storage_path, "r", encoding="utf-8") as f:
                            simulated_events = json.load(f)
                    except:
                        pass
                
                simulated_events.append({
                    "id": str(row["id"]),
                    "title": request.title,
                    "start": request.start,
                    "end": request.end,
                    "attendees": request.attendees or [],
                    "created_at": datetime.now().isoformat(),
                })
                
                with open(storage_path, "w", encoding="utf-8") as f:
                    json.dump(simulated_events, f, indent=2)
            
            # Log audit event
            await conn.execute(
                """
                INSERT INTO events (type, payload)
                VALUES ($1, $2)
                """,
                "calendar_event_created",
                json.dumps({
                    "suggestionId": request.suggestionId,
                    "eventId": str(row["id"]),
                    "googleEventId": google_event_id,
                    "source": event_source,
                    "title": request.title,
                }),
            )
        
        return {
            "success": True,
            "eventId": str(row["id"]),
            "source": event_source,
            "googleEventId": google_event_id,
        }
    except HTTPException:
        raise
    except Exception as error:
        print(f"Error creating calendar event: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to create calendar event: {str(error)}")



async def parse_event_text(text: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """
    Parse natural language text to extract calendar event details.
    Uses conversation history for context (e.g., previous mentions of meeting title, duration).
    Returns dict with 'event' (if successful) or 'missing_fields' and 'clarifying_question'.
    This is a helper function that can be called from other routes.
    """
    if not text:
        return {
            "missing_fields": ["title", "start_time"],
            "clarifying_question": "What would you like to schedule, and when?",
        }
    
    # Build context from conversation history
    context_text = ""
    if conversation_history:
        # Get last 5 messages for context
        recent_messages = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
        for msg in recent_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                context_text += f"User: {content}\n"
            elif role == "assistant":
                context_text += f"Assistant: {content}\n"
    
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    tomorrow_date_str = tomorrow.strftime("%Y-%m-%d")
    today_date_str = now.strftime("%Y-%m-%d")
    default_time = now.replace(hour=14, minute=0, second=0, microsecond=0)  # 2pm today
    
    # Build context-aware prompt
    context_instruction = ""
    if context_text:
        context_instruction = f"""
CONVERSATION CONTEXT (use this to fill in missing details):
{context_text}

IMPORTANT: Extract information from the conversation context:
- If a meeting title was mentioned earlier (e.g., "POC meeting"), use it
- If duration was mentioned (e.g., "1 hour"), use it
- If participants were mentioned (e.g., "no participants", "just me"), use empty array []
- If date/time was mentioned earlier, use it
"""
    
    system_prompt = f"""You are a helpful calendar assistant. Extract calendar event details from natural language and conversation context.

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
{context_instruction}
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
  "attendees": "array of strings or [] (use [] if not mentioned or user said 'no participants')"
}}

Examples (copy format exactly):
"Meeting tomorrow at 2pm" → {{"title":"Meeting","start_time":"{tomorrow_date_str}T14:00:00","end_time":"{tomorrow_date_str}T15:00:00","attendees":[]}}
"Schedule the POC meeting" (if context mentions "POC meeting" and "1 hour") → {{"title":"POC meeting","start_time":"{today_date_str}T14:00:00","end_time":"{today_date_str}T15:00:00","attendees":[]}}
"no, just schedule the POC meeting" (if context mentions "POC meeting", "1 hour", "no participants") → {{"title":"POC meeting","start_time":"{today_date_str}T14:00:00","end_time":"{today_date_str}T15:00:00","attendees":[]}}

Return ONLY the JSON object, nothing else."""

    try:
        # Build user message with context
        user_message = text
        if context_text:
            user_message = f"Conversation context:\n{context_text}\n\nCurrent message: {text}\n\nExtract calendar event details from the current message and conversation context above."
        
        llm_response = await generate_chat_completion(
            LLMRequestOptions(
                model=os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL", "gpt-4o-mini"),
                messages=[
                    LLMMessage("system", system_prompt),
                    LLMMessage("user", user_message),
                ],
                temperature=0.0,
                max_tokens=200,  # Increased to handle context
                use_local=False,  # Skip Ollama when using OpenAI
            )
        )
        
        # Parse LLM response
        event_data = None
        try:
            json_text = llm_response.content.strip()
            json_text = re.sub(r"```json\s*", "", json_text).replace("```", "")
            json_match = re.search(r"\{[\s\S]*\}", json_text)
            if json_match:
                event_data = json.loads(json_match.group(0))
            else:
                event_data = json.loads(json_text)
        except Exception as parse_error:
            print(f"[Calendar Parse] JSON parse error: {parse_error}")
            # Enhanced fallback parser (same as below)
            event_data = _fallback_parse_event(text)
        
        # Use smart defaults instead of asking for clarification
        if not event_data:
            event_data = {}
        
        # Default title
        if not event_data.get("title"):
            event_data["title"] = "Meeting"
        
        # Default start_time (today at 2pm)
        if not event_data.get("start_time"):
            default_start = now.replace(hour=14, minute=0, second=0, microsecond=0)
            event_data["start_time"] = default_start.isoformat()
        
        # Default end_time (1 hour after start)
        if not event_data.get("end_time"):
            start = datetime.fromisoformat(event_data["start_time"].replace("Z", "+00:00"))
            end = start + timedelta(hours=1)
            event_data["end_time"] = end.isoformat()
        
        # Default attendees (empty array)
        if "attendees" not in event_data:
            event_data["attendees"] = []
        
        # Ensure attendees is a list
        if isinstance(event_data.get("attendees"), str):
            try:
                event_data["attendees"] = json.loads(event_data["attendees"])
            except:
                event_data["attendees"] = []
        
        return {"event": event_data}
    
    except Exception as e:
        print(f"[Calendar Parse] Error: {e}")
        return {
            "missing_fields": ["title", "start_time"],
            "clarifying_question": "I'm having trouble parsing that. Could you provide the event title and time?",
        }


def _fallback_parse_event(text: str) -> Dict[str, Any]:
    """Fallback parser using regex patterns."""
    lower_text = text.lower()
    title = "Meeting"
    
    # Extract title
    title_patterns = [
        r"(?:schedule|add|create|book|plan)\s+(?:a\s+)?(?:meeting|call|appointment|event|standup|sync|review|conference)\s+(?:called|titled|named)?\s*[\"']?([^\"']+)[\"']?",
        r"(?:meeting|call|appointment|event|standup|sync|review|conference)\s+(?:called|titled|named)?\s*[\"']?([^\"']+?)(?:\s+tomorrow|\s+today|\s+at|\s+on|$)",
    ]
    
    for pattern in title_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1) and match.group(1).strip():
            title = match.group(1).strip()
            break
    
    if title == "Meeting":
        if "standup" in lower_text:
            title = "Team Standup"
        elif "call" in lower_text:
            title = "Call"
        elif "appointment" in lower_text:
            title = "Appointment"
    
    # Extract time
    start_date = datetime.now()
    hour = 14
    minute = 0
    
    if "tomorrow" in lower_text:
        start_date = datetime.now() + timedelta(days=1)
    
    time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text, re.IGNORECASE)
    if time_match:
        hour = int(time_match.group(1))
        if time_match.group(3):
            ampm = time_match.group(3).lower()
            if ampm == "pm" and hour < 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
        if time_match.group(2):
            minute = int(time_match.group(2))
    
    start_date = start_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    end_date = start_date + timedelta(hours=1)
    
    # Check for recurring
    is_recurring = "every" in lower_text or "weekly" in lower_text or "daily" in lower_text
    recurrence_pattern = None
    if is_recurring:
        if "daily" in lower_text or "every day" in lower_text:
            recurrence_pattern = "daily"
        elif "weekly" in lower_text or "every week" in lower_text:
            recurrence_pattern = "weekly"
        elif "monthly" in lower_text:
            recurrence_pattern = "monthly"
        else:
            recurrence_pattern = "weekly"
    
    return {
        "title": title[:100],
        "start_time": start_date.isoformat(),
        "end_time": end_date.isoformat(),
        "is_recurring": is_recurring,
        "recurrence_pattern": recurrence_pattern,
    }


@router.post("/parse")
async def parse_event(request: ParseEventRequest):
    """
    Parse natural language to create calendar event - DEPRECATED.
    
    This endpoint is deprecated. Use POST /api/v1/scheduler/parse instead.
    """
    warnings.warn(
        "POST /api/calendar/parse is deprecated. Use POST /api/v1/scheduler/parse instead.",
        DeprecationWarning,
        stacklevel=2
    )
    try:
        text = request.text
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")

        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        tomorrow_date_str = tomorrow.strftime("%Y-%m-%d")

        system_prompt = f"""You are a strict JSON parser. Extract calendar event details from natural language.

CRITICAL RULES:
1. Return ONLY valid JSON - no explanations, no markdown, no code blocks
2. Start with {{ and end with }}
3. Use double quotes for all strings
4. Calculate dates relative to: {now.isoformat()}
5. Tomorrow is: {tomorrow_date_str}

JSON Schema:
{{
  "title": "string (required)",
  "start_time": "ISO 8601 datetime (required)",
  "end_time": "ISO 8601 datetime (required, default: 1 hour after start)",
  "description": "string or null",
  "is_recurring": "boolean",
  "recurrence_pattern": "daily|weekly|monthly|yearly or null",
  "recurrence_interval": "number (default 1)",
  "location": "string or null",
  "attendees": "array of strings or null"
}}

Examples (copy format exactly):
"Meeting tomorrow at 2pm" → {{"title":"Meeting","start_time":"{tomorrow_date_str}T14:00:00","end_time":"{tomorrow_date_str}T15:00:00"}}
"Standup every Monday 9am" → {{"title":"Standup","start_time":"2024-11-25T09:00:00","end_time":"2024-11-25T09:30:00","is_recurring":true,"recurrence_pattern":"weekly"}}

Return ONLY the JSON object, nothing else."""

        llm_response = await generate_chat_completion(
            LLMRequestOptions(
                model=os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL", "gpt-4o-mini"),
                messages=[
                    LLMMessage("system", system_prompt),
                    LLMMessage("user", text),
                ],
                temperature=0.0,
                max_tokens=150,
                use_local=False,  # Skip Ollama when using OpenAI
            )
        )

        # Parse LLM response
        event_data = None
        try:
            json_text = llm_response.content.strip()
            json_text = re.sub(r"```json\s*", "", json_text).replace("```", "")
            json_match = re.search(r"\{[\s\S]*\}", json_text)
            if json_match:
                event_data = json.loads(json_match.group(0))
            else:
                event_data = json.loads(json_text)
        except Exception as parse_error:
            print(f"[Calendar Parse] JSON parse error: {parse_error}")
            # Enhanced fallback parser
            lower_text = text.lower()
            title = "Meeting"

            # Extract title
            title_patterns = [
                r"(?:schedule|add|create|book|plan)\s+(?:a\s+)?(?:meeting|call|appointment|event|standup|sync|review|conference)\s+(?:called|titled|named)?\s*[\"']?([^\"']+)[\"']?",
                r"(?:meeting|call|appointment|event|standup|sync|review|conference)\s+(?:called|titled|named)?\s*[\"']?([^\"']+?)(?:\s+tomorrow|\s+today|\s+at|\s+on|$)",
            ]

            for pattern in title_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match and match.group(1) and match.group(1).strip():
                    title = match.group(1).strip()
                    break

            if title == "Meeting":
                if "standup" in lower_text:
                    title = "Team Standup"
                elif "call" in lower_text:
                    title = "Call"
                elif "appointment" in lower_text:
                    title = "Appointment"

            # Extract time
            start_date = datetime.now()
            hour = 14
            minute = 0

            if "tomorrow" in lower_text:
                start_date = datetime.now() + timedelta(days=1)

            time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text, re.IGNORECASE)
            if time_match:
                hour = int(time_match.group(1))
                if time_match.group(3):
                    ampm = time_match.group(3).lower()
                    if ampm == "pm" and hour < 12:
                        hour += 12
                    elif ampm == "am" and hour == 12:
                        hour = 0
                if time_match.group(2):
                    minute = int(time_match.group(2))

            start_date = start_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            end_date = start_date + timedelta(hours=1)

            # Check for recurring
            is_recurring = "every" in lower_text or "weekly" in lower_text or "daily" in lower_text
            recurrence_pattern = None
            if is_recurring:
                if "daily" in lower_text or "every day" in lower_text:
                    recurrence_pattern = "daily"
                elif "weekly" in lower_text or "every week" in lower_text:
                    recurrence_pattern = "weekly"
                elif "monthly" in lower_text:
                    recurrence_pattern = "monthly"
                else:
                    recurrence_pattern = "weekly"

            event_data = {
                "title": title[:100],
                "start_time": start_date.isoformat(),
                "end_time": end_date.isoformat(),
                "is_recurring": is_recurring,
                "recurrence_pattern": recurrence_pattern,
            }

        if not event_data or not event_data.get("title") or not event_data.get("start_time"):
            raise HTTPException(
                status_code=400,
                detail="Could not extract required fields (title, start_time)",
            )

        # Set default end_time
        if not event_data.get("end_time"):
            start = datetime.fromisoformat(event_data["start_time"].replace("Z", "+00:00"))
            end = start + timedelta(hours=1)
            event_data["end_time"] = end.isoformat()

        # Create the event
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO calendar_events 
                (title, description, start_time, end_time, is_recurring, recurrence_pattern, 
                 recurrence_end_date, recurrence_interval, location, attendees)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING *
                """,
                event_data["title"],
                event_data.get("description"),
                datetime.fromisoformat(event_data["start_time"].replace("Z", "+00:00")),
                datetime.fromisoformat(event_data["end_time"].replace("Z", "+00:00")),
                event_data.get("is_recurring", False),
                event_data.get("recurrence_pattern"),
                datetime.fromisoformat(event_data["recurrence_end_date"].replace("Z", "+00:00"))
                if event_data.get("recurrence_end_date")
                else None,
                event_data.get("recurrence_interval", 1),
                event_data.get("location"),
                json.dumps(event_data.get("attendees", [])),
            )

            return {"event": dict(row), "parsed": event_data}
    except HTTPException:
        raise
    except Exception as error:
        print(f"Error parsing calendar event: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to parse calendar event: {str(error)}")


@router.put("/events/{event_id}")
async def update_event(event_id: str, updates: Dict[str, Any]):
    """Update a calendar event."""
    try:
        allowed_fields = [
            "title",
            "description",
            "start_time",
            "end_time",
            "is_recurring",
            "recurrence_pattern",
            "recurrence_end_date",
            "recurrence_interval",
            "location",
            "attendees",
        ]

        update_fields = []
        values = []
        param_index = 1

        for field in allowed_fields:
            if field in updates:
                update_fields.append(f"{field} = ${param_index}")
                if field == "attendees":
                    values.append(json.dumps(updates[field]))
                elif "_time" in field or "_date" in field:
                    values.append(datetime.fromisoformat(updates[field].replace("Z", "+00:00")))
                else:
                    values.append(updates[field])
                param_index += 1

        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        update_fields.append("updated_at = NOW()")
        values.append(event_id)

        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"UPDATE calendar_events SET {', '.join(update_fields)} WHERE id = ${param_index} RETURNING *",
                *values,
            )

            return {"event": dict(row)}
    except HTTPException:
        raise
    except Exception as error:
        print(f"Error updating calendar event: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to update calendar event: {str(error)}")


@router.delete("/events/{event_id}")
async def delete_event(event_id: str):
    """Delete a calendar event."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM calendar_events WHERE id = $1", event_id)
            return {"success": True}
    except Exception as error:
        print(f"Error deleting calendar event: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to delete calendar event: {str(error)}")

