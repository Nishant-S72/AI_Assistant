"""Priority computation for tasks with deterministic scoring and reason tracking."""
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta


def compute_priority(context: Dict[str, Any]) -> str:
    """
    Compute task priority based on context.
    Returns: 'P0', 'P1', 'P2', or 'P3'
    
    Deprecated: Use compute_priority_with_reason() for new code.
    """
    priority, _ = compute_priority_with_reason(context)
    return priority


def compute_priority_with_reason(context: Dict[str, Any]) -> Tuple[str, str]:
    """
    Compute task priority with deterministic scoring and reason.
    
    Scoring Rules:
    - P0 = <24 hours OR explicit urgency
    - P1 = <3 days OR moderate urgency indicators
    - P2 = default
    
    Returns:
        (priority: 'P0'|'P1'|'P2'|'P3', reason: str)
    """
    task = context.get("task", {})
    message = context.get("message", {})
    contact = context.get("contact", {})

    due_at = task.get("due_at")
    title = task.get("title", "").lower()
    message_body = message.get("body", "").lower()
    contact_tags = contact.get("tags", [])
    last_order_amount = contact.get("last_order_amount", 0)
    
    now = datetime.now(timezone.utc)

    # P0: Overdue or <24 hours
    if due_at:
        try:
            due_date = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
            if due_date < now:
                return "P0", f"Task is overdue (due: {due_date.date()})"
            
            hours_until_due = (due_date - now).total_seconds() / 3600
            if hours_until_due < 24:
                return "P0", f"Task due within 24 hours ({hours_until_due:.1f} hours remaining)"
        except Exception:
            pass

    # P0: Explicit urgency indicators
    urgent_tags = ["urgent-action-required", "escalation"]
    if any(tag.lower() in [t.lower() for t in contact_tags] for tag in urgent_tags):
        matched_tag = next(tag for tag in urgent_tags if tag.lower() in [t.lower() for t in contact_tags])
        return "P0", f"Contact tagged as '{matched_tag}'"
    
    urgent_keywords = ["urgent", "asap", "immediately", "critical", "emergency"]
    matched_keyword = next((kw for kw in urgent_keywords if kw in title or kw in message_body), None)
    if matched_keyword:
        return "P0", f"Explicit urgency keyword detected: '{matched_keyword}'"

    # P1: <3 days OR moderate urgency indicators
    if due_at:
        try:
            due_date = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
            days_until_due = (due_date - now).total_seconds() / 86400
            if days_until_due < 3:
                return "P1", f"Task due within 3 days ({days_until_due:.1f} days remaining)"
        except Exception:
            pass

    # P1: High-priority tags or high-value contacts
    high_priority_tags = ["high-priority"]
    if any(tag.lower() in [t.lower() for t in contact_tags] for tag in high_priority_tags):
        return "P1", "Contact tagged as 'high-priority'"
    
    high_value_tags = ["vip", "enterprise", "high value", "key account"]
    if any(tag.lower() in [t.lower() for t in contact_tags] for tag in high_value_tags):
        matched_tag = next(tag for tag in high_value_tags if tag.lower() in [t.lower() for t in contact_tags])
        return "P1", f"High-value contact tagged as '{matched_tag}'"

    if last_order_amount > 10000:
        return "P1", f"High-value customer (last order: ${last_order_amount:,.0f})"

    important_keywords = ["important", "priority", "escalate", "complaint"]
    matched_keyword = next((kw for kw in important_keywords if kw in title or kw in message_body), None)
    if matched_keyword:
        return "P1", f"Important keyword detected: '{matched_keyword}'"

    # P2: Has due date (beyond 3 days) or lead tags
    if due_at:
        return "P2", "Task has due date set"

    lead_tags = ["new-lead", "potential-interest", "lead", "prospect", "potential"]
    if any(tag.lower() in [t.lower() for t in contact_tags] for tag in lead_tags):
        matched_tag = next(tag for tag in lead_tags if tag.lower() in [t.lower() for t in contact_tags])
        return "P2", f"Contact tagged as '{matched_tag}'"

    # P2: Default
    return "P2", "Standard priority (no urgency indicators)"

