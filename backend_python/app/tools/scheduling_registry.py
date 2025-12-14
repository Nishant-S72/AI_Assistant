"""Register scheduling tools in the function registry."""
from app.tools.registry import get_registry
from app.tools.scheduling_handlers import (
    parse_schedule,
    create_event,
    find_availability,
    reschedule_event,
    cancel_event,
    create_reminder,
)


def register_scheduling_tools():
    """Register all scheduling tools in the global registry."""
    registry = get_registry()
    
    # Register parse_schedule
    if not registry.get_tool("parse_schedule"):
        registry.register_tool(
            name="parse_schedule",
            schema={
                "description": "Parse natural language scheduling request into structured format. Use this when the user wants to schedule something but hasn't provided all details yet.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "natural_language": {
                            "type": "string",
                            "description": "User's scheduling request in natural language (e.g., 'Schedule a meeting tomorrow at 2pm with John')"
                        },
                        "user_id": {
                            "type": "string",
                            "description": "User ID (optional, will be provided by system)"
                        },
                    },
                    "required": ["natural_language"],
                },
            },
            handler=parse_schedule,
        )
    
    # Register create_event
    if not registry.get_tool("create_event"):
        registry.register_tool(
            name="create_event",
            schema={
                "description": "Create a calendar event. Use this when the user wants to schedule a meeting, appointment, or event.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Event title or subject"
                        },
                        "start_time": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Event start time in ISO 8601 format (e.g., '2024-01-15T14:00:00Z')"
                        },
                        "end_time": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Event end time in ISO 8601 format"
                        },
                        "user_id": {
                            "type": "string",
                            "description": "User ID (will be provided by system)"
                        },
                        "calendar_provider": {
                            "type": "string",
                            "enum": ["google", "outlook"],
                            "description": "Calendar provider to use (default: google)"
                        },
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of attendee email addresses"
                        },
                        "location": {
                            "type": "string",
                            "description": "Event location (optional)"
                        },
                        "description": {
                            "type": "string",
                            "description": "Event description or notes (optional)"
                        },
                        "timezone": {
                            "type": "string",
                            "description": "Timezone (e.g., 'America/New_York', default: UTC)"
                        },
                        "recurrence_rule": {
                            "type": "string",
                            "description": "RRULE string for recurring events (optional, e.g., 'FREQ=WEEKLY;BYDAY=MO')"
                        },
                    },
                    "required": ["title", "start_time", "end_time", "user_id"],
                },
            },
            handler=create_event,
        )
    
    # Register find_availability
    if not registry.get_tool("find_availability"):
        registry.register_tool(
            name="find_availability",
            schema={
                "description": "Find available time slots in the user's calendar. Use this when the user asks about free time or wants to find a good time for a meeting.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "User ID (will be provided by system)"
                        },
                        "start_date": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Start of date range to search (ISO format)"
                        },
                        "end_date": {
                            "type": "string",
                            "format": "date-time",
                            "description": "End of date range to search (ISO format)"
                        },
                        "duration_minutes": {
                            "type": "integer",
                            "description": "Duration of the meeting in minutes (default: 60)"
                        },
                        "calendar_provider": {
                            "type": "string",
                            "enum": ["google", "outlook"],
                            "description": "Calendar provider to check (default: google)"
                        },
                    },
                    "required": ["user_id", "start_date", "end_date"],
                },
            },
            handler=find_availability,
        )
    
    # Register reschedule_event
    if not registry.get_tool("reschedule_event"):
        registry.register_tool(
            name="reschedule_event",
            schema={
                "description": "Reschedule an existing event to a new time. Use this when the user wants to move a meeting to a different time.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_id": {
                            "type": "string",
                            "description": "Event ID (from event_mirror table)"
                        },
                        "new_start_time": {
                            "type": "string",
                            "format": "date-time",
                            "description": "New start time (ISO format)"
                        },
                        "new_end_time": {
                            "type": "string",
                            "format": "date-time",
                            "description": "New end time (ISO format)"
                        },
                        "user_id": {
                            "type": "string",
                            "description": "User ID (will be provided by system)"
                        },
                    },
                    "required": ["event_id", "new_start_time", "new_end_time", "user_id"],
                },
            },
            handler=reschedule_event,
        )
    
    # Register cancel_event
    if not registry.get_tool("cancel_event"):
        registry.register_tool(
            name="cancel_event",
            schema={
                "description": "Cancel or delete an event. Use this when the user wants to cancel a meeting or event.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_id": {
                            "type": "string",
                            "description": "Event ID (from event_mirror table)"
                        },
                        "user_id": {
                            "type": "string",
                            "description": "User ID (will be provided by system)"
                        },
                    },
                    "required": ["event_id", "user_id"],
                },
            },
            handler=cancel_event,
        )
    
    # Register create_reminder
    if not registry.get_tool("create_reminder"):
        registry.register_tool(
            name="create_reminder",
            schema={
                "description": "Create a reminder for an event. Use this when the user wants to be reminded about an event.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_id": {
                            "type": "string",
                            "description": "Event ID to create reminder for"
                        },
                        "user_id": {
                            "type": "string",
                            "description": "User ID (will be provided by system)"
                        },
                        "reminder_type": {
                            "type": "string",
                            "enum": ["email", "slack", "in_app"],
                            "description": "Type of reminder notification"
                        },
                        "minutes_before": {
                            "type": "integer",
                            "description": "Minutes before event to trigger reminder (e.g., 15, 60)"
                        },
                        "message": {
                            "type": "string",
                            "description": "Custom reminder message (optional)"
                        },
                    },
                    "required": ["event_id", "user_id", "reminder_type", "minutes_before"],
                },
            },
            handler=create_reminder,
        )
    
    print("[SchedulingRegistry] Registered all scheduling tools")


# Auto-register on import
register_scheduling_tools()


