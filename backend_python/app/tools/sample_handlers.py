"""Sample tool handlers for function calling."""
from typing import Dict, Any, List


async def send_email_stub(to: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Send email (stub implementation).
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body
    
    Returns:
        Dict with success status and message_id
    """
    # TODO: Implement actual email sending
    return {
        "success": True,
        "message_id": f"stub-{to}-{subject[:10]}",
        "to": to,
        "subject": subject,
    }


async def get_calendar_events(range_start: str, range_end: str) -> List[Dict[str, Any]]:
    """
    Get calendar events in date range.
    
    Args:
        range_start: Start date (ISO format)
        range_end: End date (ISO format)
    
    Returns:
        List of calendar event dicts
    """
    # TODO: Implement actual calendar fetch
    return [
        {
            "id": "stub-1",
            "title": "Sample Event",
            "start": range_start,
            "end": range_end,
        }
    ]


