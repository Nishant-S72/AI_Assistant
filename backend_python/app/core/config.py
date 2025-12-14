"""
Core configuration constants and settings.
"""
import os
from typing import Literal
from enum import Enum

# Tier definitions
class UserTier(str, Enum):
    ASSIST = "assist"
    PRO = "pro"

# Tier pricing
TIER_PRICING = {
    UserTier.ASSIST: 500,
    UserTier.PRO: 1000,
}

# Assist tier allowed actions
ASSIST_ALLOWED_ACTIONS = {
    "inbox_ingestion",
    "thread_summarization",
    "draft_replies",
    "tone_selection",
    "priority_classification",
    "suggested_next_actions",
    "rag_read_only",
}

# Assist tier forbidden actions
ASSIST_FORBIDDEN_ACTIONS = {
    "auto_send_emails",
    "calendar_creation",
    "task_creation",
    "follow_ups",
    "workflow_execution",
    "memory_updates",
}

# Pro tier gets everything
PRO_ALLOWED_ACTIONS = ASSIST_ALLOWED_ACTIONS | {
    "auto_send",
    "calendar_event_creation",
    "task_creation",
    "follow_up_scheduling",
    "behavioural_memory",
    "multi_step_workflows",
}

# Intent classification
INTENT_LABELS = ["general", "rag", "action_candidate"]
INTENT_CONFIDENCE_THRESHOLD = 0.65

# Action types
ACTION_TYPES = {
    "send_email",
    "create_calendar_event",
    "create_task",
    "schedule_followup",
}

# LLM Model assignments
LLM_MODEL_ASSIGNMENTS = {
    "thread_summaries": os.getenv("GEMINI_MODEL", "gpt-4o-mini"),
    "priority_classification": os.getenv("GEMINI_MODEL", "gpt-4o-mini"),
    "draft_replies": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    "intent_classification": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    "action_planning": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    "rag_answer_synthesis": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
}

# Fallback: if only one model available, use it everywhere
DEFAULT_LLM_MODEL = os.getenv("OPENAI_MODEL") or os.getenv("GEMINI_MODEL") or "gpt-4o-mini"

# RAG settings
RAG_TOP_K = 3
RAG_CITATION_TOKEN_PATTERN = "[ref{index}]"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "json"  # Structured JSON logging

