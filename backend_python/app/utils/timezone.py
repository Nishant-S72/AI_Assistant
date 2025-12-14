"""
Timezone normalization utilities for calendar events.
All backend timestamps stored in UTC, frontend displays in user timezone.
"""
from typing import Optional
from datetime import datetime
try:
    import pytz
except ImportError:
    pytz = None
try:
    from dateutil import tz
except ImportError:
    tz = None


def normalize_to_utc(dt: datetime, timezone_str: Optional[str] = None) -> datetime:
    """
    Normalize a datetime to UTC.
    
    Args:
        dt: Datetime object (may be naive or timezone-aware)
        timezone_str: Optional IANA timezone string (e.g., "America/New_York")
    
    Returns:
        UTC datetime (timezone-aware)
    """
    if dt.tzinfo is None:
        # Naive datetime - assume it's in the provided timezone or UTC
        if timezone_str:
            tz_obj = pytz.timezone(timezone_str)
            dt = tz_obj.localize(dt)
        else:
            # Assume UTC if no timezone provided
            dt = pytz.UTC.localize(dt)
    
    # Convert to UTC
    return dt.astimezone(pytz.UTC)


def convert_from_utc(utc_dt: datetime, target_timezone_str: str) -> datetime:
    """
    Convert UTC datetime to target timezone.
    
    Args:
        utc_dt: UTC datetime (timezone-aware)
        target_timezone_str: Target IANA timezone string
    
    Returns:
        Datetime in target timezone
    """
    if pytz is None:
        # Fallback: return as-is if pytz not available
        return utc_dt
    
    if utc_dt.tzinfo is None:
        # Assume UTC if naive
        utc_dt = pytz.UTC.localize(utc_dt)
    
    target_tz = pytz.timezone(target_timezone_str)
    return utc_dt.astimezone(target_tz)


def handle_dst_transition(dt: datetime, timezone_str: str) -> datetime:
    """
    Handle DST (Daylight Saving Time) transitions correctly.
    
    Args:
        dt: Datetime object
        timezone_str: IANA timezone string
    
    Returns:
        Corrected datetime accounting for DST
    """
    if pytz is None:
        # Fallback: return as-is if pytz not available
        return dt
    
    tz_obj = pytz.timezone(timezone_str)
    
    if dt.tzinfo is None:
        # Localize naive datetime
        dt = tz_obj.localize(dt)
    else:
        # Convert to target timezone
        dt = dt.astimezone(tz_obj)
    
    return dt


def parse_recurrence_rule(rrule_str: Optional[str]) -> dict:
    """
    Parse iCal RRULE string into structured format.
    
    Args:
        rrule_str: RRULE string (e.g., "FREQ=DAILY;INTERVAL=1;COUNT=10")
    
    Returns:
        Dictionary with parsed rule components
    """
    if not rrule_str:
        return {}
    
    rule_parts = {}
    for part in rrule_str.split(';'):
        if '=' in part:
            key, value = part.split('=', 1)
            rule_parts[key.upper()] = value
    
    return rule_parts


def format_recurrence_rule(rule_dict: dict) -> str:
    """
    Format structured recurrence rule back to RRULE string.
    
    Args:
        rule_dict: Dictionary with rule components
    
    Returns:
        RRULE string
    """
    if not rule_dict:
        return ""
    
    parts = [f"{k}={v}" for k, v in rule_dict.items()]
    return ";".join(parts)


def prevent_duplicate_import(
    source_event_id: str,
    normalized_start_time: datetime,
    title: str,
) -> str:
    """
    Generate a deterministic key to prevent duplicate event imports.
    
    Args:
        source_event_id: External event ID
        normalized_start_time: Start time normalized to UTC
        title: Event title
    
    Returns:
        Unique key for deduplication
    """
    # Normalize title (lowercase, strip whitespace)
    normalized_title = title.lower().strip()
    
    # Format start time as ISO string (UTC)
    start_iso = normalized_start_time.isoformat()
    
    # Create deterministic key
    return f"{source_event_id}|{start_iso}|{normalized_title}"

