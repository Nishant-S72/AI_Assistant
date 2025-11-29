"""Priority computation for tasks."""
from typing import Dict, Any, Optional
from datetime import datetime, timezone


def compute_priority(context: Dict[str, Any]) -> str:
    """
    Compute task priority based on context.
    Returns: 'P0', 'P1', 'P2', or 'P3'
    """
    task = context.get("task", {})
    message = context.get("message", {})
    contact = context.get("contact", {})

    due_at = task.get("due_at")
    title = task.get("title", "").lower()
    message_body = message.get("body", "").lower()
    contact_tags = contact.get("tags", [])
    last_order_amount = contact.get("last_order_amount", 0)

    # P0: Overdue or urgent keywords
    if due_at:
        try:
            due_date = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if due_date < now:
                return "P0"
        except Exception:
            pass

    urgent_keywords = ["urgent", "asap", "immediately", "critical", "emergency"]
    if any(keyword in title or keyword in message_body for keyword in urgent_keywords):
        return "P0"

    # P1: High-value contacts or important keywords
    high_value_tags = ["vip", "enterprise", "high value", "key account"]
    if any(tag.lower() in [t.lower() for t in contact_tags] for tag in high_value_tags):
        return "P1"

    if last_order_amount > 10000:  # High-value customer
        return "P1"

    important_keywords = ["important", "priority", "escalate", "complaint"]
    if any(keyword in title or keyword in message_body for keyword in important_keywords):
        return "P1"

    # P2: Has due date or lead tags
    if due_at:
        return "P2"

    lead_tags = ["lead", "prospect", "potential"]
    if any(tag.lower() in [t.lower() for t in contact_tags] for tag in lead_tags):
        return "P2"

    # P3: Default
    return "P3"

