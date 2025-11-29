"""Calendar routes."""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.db.connection import get_pool
from app.clients.llm import generate_chat_completion, LLMMessage, LLMRequestOptions
import json
import os
import re


class CreateEventRequest(BaseModel):
    """Request model for creating a calendar event."""
    title: str
    description: Optional[str] = None
    start_time: str
    end_time: str
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None
    recurrence_end_date: Optional[str] = None
    recurrence_interval: int = 1
    location: Optional[str] = None
    attendees: Optional[List[str]] = None


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
            # Simple monthly increment
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + interval)
        elif pattern == "yearly":
            current = current.replace(year=current.year + interval)
        else:
            break

    return instances


@router.get("/events")
async def get_events(start: str = Query(...), end: str = Query(...)):
    """Get events for a date range."""
    try:
        start_date = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_date = datetime.fromisoformat(end.replace("Z", "+00:00"))

        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM calendar_events 
                WHERE (start_time >= $1 AND start_time <= $2)
                   OR (is_recurring = true AND recurrence_end_date >= $1)
                ORDER BY start_time ASC
                """,
                start_date,
                end_date,
            )

        # Expand recurring events
        events = []
        for row in rows:
            event = dict(row)
            if event.get("is_recurring") and event.get("recurrence_pattern"):
                instances = generate_recurring_instances(event, start_date, end_date)
                events.extend(instances)
            else:
                events.append(event)

        events.sort(key=lambda e: datetime.fromisoformat(e["start_time"].replace("Z", "+00:00")))
        return {"events": events}
    except Exception as error:
        print(f"Error fetching calendar events: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch calendar events: {str(error)}")


@router.post("/events")
async def create_event(request: CreateEventRequest):
    """Create a new calendar event."""
    try:
        title = request.title
        start_time = request.start_time
        end_time = request.end_time

        if not title or not start_time or not end_time:
            raise HTTPException(status_code=400, detail="Title, start_time, and end_time are required")

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
                title,
                request.description,
                datetime.fromisoformat(start_time.replace("Z", "+00:00")),
                datetime.fromisoformat(end_time.replace("Z", "+00:00")),
                request.is_recurring,
                request.recurrence_pattern,
                datetime.fromisoformat(request.recurrence_end_date.replace("Z", "+00:00"))
                if request.recurrence_end_date
                else None,
                request.recurrence_interval,
                request.location,
                json.dumps(request.attendees or []),
            )

            return {"event": dict(row)}
    except HTTPException:
        raise
    except Exception as error:
        print(f"Error creating calendar event: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to create calendar event: {str(error)}")


@router.post("/parse")
async def parse_event(request: ParseEventRequest):
    """Parse natural language to create calendar event."""
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
                model=os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or "tinyllama",
                messages=[
                    LLMMessage("system", system_prompt),
                    LLMMessage("user", text),
                ],
                temperature=0.0,
                max_tokens=150,
                use_local=os.getenv("USE_OLLAMA") != "false",
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

