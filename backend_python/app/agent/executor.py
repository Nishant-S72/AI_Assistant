"""
Action Executor - Executes planned actions (Pro tier only).
"""
from typing import Dict, Any, Optional
from app.core.config import UserTier
from app.core.errors import TierRestrictionError, ActionExecutionError, ValidationError
from app.core.logger import logger
from app.middleware.tier_gating import get_user_tier
from app.services.email_service import send_email
from app.services.calendar_service import create_calendar_event
from app.services.tasks_service import create_task
import uuid


async def execute_action(
    action_type: str,
    parameters: Dict[str, Any],
    user_id: str,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a planned action.
    
    Args:
        action_type: Type of action to execute
        parameters: Action parameters
        user_id: User ID
        correlation_id: Optional correlation ID
    
    Returns:
        {
            "executed": bool,
            "result": Dict[str, Any],
            "error": Optional[str],
        }
    """
    # Check tier
    tier = await get_user_tier(user_id)
    
    if tier != UserTier.PRO:
        logger.warning(
            f"Tier restriction: {action_type} requires Pro tier",
            extra={
                "user_id": user_id,
                "tier": tier.value,
                "action_type": action_type,
                "correlation_id": correlation_id,
            }
        )
        return {
            "executed": False,
            "reason": "TIER_RESTRICTION",
            "message": f"This action requires Pro tier. Current tier: {tier.value}",
            "current_tier": tier.value,
            "required_tier": "pro",
        }
    
    logger.info(
        f"Executing action: {action_type}",
        extra={
            "user_id": user_id,
            "action_type": action_type,
            "correlation_id": correlation_id,
        }
    )
    
    try:
        if action_type == "send_email":
            result = await _execute_send_email(parameters, user_id)
        elif action_type == "create_calendar_event":
            result = await _execute_create_calendar_event(parameters, user_id)
        elif action_type == "create_task":
            result = await _execute_create_task(parameters, user_id)
        elif action_type == "schedule_followup":
            result = await _execute_schedule_followup(parameters, user_id)
        else:
            raise ActionExecutionError(
                f"Unknown action type: {action_type}",
                action_type=action_type
            )
        
        logger.info(
            f"Action executed successfully: {action_type}",
            extra={
                "user_id": user_id,
                "action_type": action_type,
                "result_id": result.get("id"),
                "correlation_id": correlation_id,
            }
        )
        
        return {
            "executed": True,
            "result": result,
        }
        
    except ValidationError as e:
        logger.error(
            f"Action validation failed: {action_type}",
            extra={
                "user_id": user_id,
                "action_type": action_type,
                "error": str(e),
                "correlation_id": correlation_id,
            }
        )
        return {
            "executed": False,
            "reason": "VALIDATION_ERROR",
            "error": str(e),
        }
        
    except Exception as e:
        logger.error(
            f"Action execution failed: {action_type}",
            extra={
                "user_id": user_id,
                "action_type": action_type,
                "error": str(e),
                "correlation_id": correlation_id,
            }
        )
        return {
            "executed": False,
            "reason": "EXECUTION_ERROR",
            "error": str(e),
        }


async def _execute_send_email(parameters: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Execute send_email action."""
    # Validate required fields
    required = ["to", "subject", "body"]
    missing = [f for f in required if f not in parameters or not parameters[f]]
    
    if missing:
        raise ValidationError(f"Missing required fields: {missing}", field="parameters")
    
    result = await send_email(
        to=parameters["to"],
        subject=parameters["subject"],
        body=parameters["body"],
        thread_id=parameters.get("thread_id"),
        user_id=user_id,
    )
    
    return result


async def _execute_create_calendar_event(parameters: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Execute create_calendar_event action."""
    required = ["title", "start_time"]
    missing = [f for f in required if f not in parameters or not parameters[f]]
    
    if missing:
        raise ValidationError(f"Missing required fields: {missing}", field="parameters")
    
    result = await create_calendar_event(
        title=parameters["title"],
        start_time=parameters["start_time"],
        end_time=parameters.get("end_time"),
        attendees=parameters.get("attendees", []),
        location=parameters.get("location"),
        description=parameters.get("description"),
        user_id=user_id,
    )
    
    return result


async def _execute_create_task(parameters: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Execute create_task action."""
    required = ["title"]
    missing = [f for f in required if f not in parameters or not parameters[f]]
    
    if missing:
        raise ValidationError(f"Missing required fields: {missing}", field="parameters")
    
    result = await create_task(
        title=parameters["title"],
        description=parameters.get("description"),
        due_date=parameters.get("due_date"),
        priority=parameters.get("priority"),
        contact_id=parameters.get("contact_id"),
        user_id=user_id,
    )
    
    return result


async def _execute_schedule_followup(parameters: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Execute schedule_followup action."""
    required = ["thread_id", "followup_date"]
    missing = [f for f in required if f not in parameters or not parameters[f]]
    
    if missing:
        raise ValidationError(f"Missing required fields: {missing}", field="parameters")
    
    # TODO: Implement followup scheduling service
    # For now, return a placeholder
    return {
        "id": str(uuid.uuid4()),
        "thread_id": parameters["thread_id"],
        "followup_date": parameters["followup_date"],
        "status": "scheduled",
    }

