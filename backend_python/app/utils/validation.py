"""
Validation utilities for action plans and data.
"""
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from email.utils import parseaddr


def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email or not isinstance(email, str):
        return False
    # Basic email regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def validate_future_datetime(dt_str: str) -> tuple[bool, Optional[str]]:
    """
    Validate that a datetime string is in the future.
    
    Returns:
        (is_valid, error_message)
    """
    try:
        # Try parsing ISO 8601 format
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        
        if dt <= now:
            return False, f"Datetime {dt_str} must be in the future"
        
        return True, None
    except (ValueError, AttributeError) as e:
        return False, f"Invalid datetime format: {dt_str} - {str(e)}"


def validate_datetime_range(start_str: str, end_str: str) -> tuple[bool, Optional[str]]:
    """
    Validate that end_time is after start_time.
    
    Returns:
        (is_valid, error_message)
    """
    try:
        start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
        
        if end <= start:
            return False, f"end_time {end_str} must be after start_time {start_str}"
        
        return True, None
    except (ValueError, AttributeError) as e:
        return False, f"Invalid datetime format: {str(e)}"


def validate_action_plan(plan: Dict[str, Any]) -> tuple[bool, List[str], List[str]]:
    """
    Validate an action plan schema and data.
    
    Returns:
        (is_valid, validation_errors, missing_fields)
    """
    errors = []
    missing_fields = []
    
    action_type = plan.get("action_type", "").lower()
    
    if not action_type:
        errors.append("action_type is required")
        missing_fields.append("action_type")
        return False, errors, missing_fields
    
    parameters = plan.get("parameters", {})
    
    # Validate based on action type
    if action_type == "send_email":
        if "recipient_email" not in parameters:
            missing_fields.append("recipient_email")
        elif not validate_email(parameters["recipient_email"]):
            errors.append(f"Invalid email format: {parameters['recipient_email']}")
        
        if "subject" not in parameters or not parameters["subject"]:
            missing_fields.append("subject")
        
        if "body" not in parameters or not parameters["body"]:
            missing_fields.append("body")
    
    elif action_type == "create_calendar_event":
        if "title" not in parameters or not parameters["title"]:
            missing_fields.append("title")
        
        if "start_time" not in parameters:
            missing_fields.append("start_time")
        else:
            is_valid, error_msg = validate_future_datetime(parameters["start_time"])
            if not is_valid:
                errors.append(error_msg)
        
        if "end_time" not in parameters:
            missing_fields.append("end_time")
        else:
            is_valid, error_msg = validate_future_datetime(parameters["end_time"])
            if not is_valid:
                errors.append(error_msg)
            
            # Validate range if both present
            if "start_time" in parameters:
                is_valid, error_msg = validate_datetime_range(
                    parameters["start_time"],
                    parameters["end_time"]
                )
                if not is_valid:
                    errors.append(error_msg)
        
        # Validate attendees if present
        if "attendees" in parameters:
            if isinstance(parameters["attendees"], list):
                for i, attendee in enumerate(parameters["attendees"]):
                    if isinstance(attendee, str):
                        if not validate_email(attendee):
                            errors.append(f"Invalid attendee email at index {i}: {attendee}")
                    elif isinstance(attendee, dict):
                        email = attendee.get("email", "")
                        if not validate_email(email):
                            errors.append(f"Invalid attendee email at index {i}: {email}")
    
    elif action_type == "create_task":
        if "title" not in parameters or not parameters["title"]:
            missing_fields.append("title")
        
        if "due_date" in parameters and parameters["due_date"]:
            # Validate date format (can be date or datetime)
            try:
                dt = datetime.fromisoformat(parameters["due_date"].replace('Z', '+00:00'))
                now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
                if dt.date() < now.date():
                    errors.append(f"due_date {parameters['due_date']} must be in the future")
            except (ValueError, AttributeError):
                errors.append(f"Invalid date format: {parameters['due_date']}")
        
        if "priority" in parameters:
            valid_priorities = ["P0", "P1", "P2"]
            if parameters["priority"] not in valid_priorities:
                errors.append(f"Invalid priority: {parameters['priority']}. Must be one of {valid_priorities}")
    
    elif action_type == "schedule_followup":
        if "recipient_email" not in parameters:
            missing_fields.append("recipient_email")
        elif not validate_email(parameters["recipient_email"]):
            errors.append(f"Invalid email format: {parameters['recipient_email']}")
        
        if "due_time" not in parameters:
            missing_fields.append("due_time")
        else:
            is_valid, error_msg = validate_future_datetime(parameters["due_time"])
            if not is_valid:
                errors.append(error_msg)
    
    is_valid = len(errors) == 0 and len(missing_fields) == 0
    
    return is_valid, errors, missing_fields

