"""
Custom error classes for the application.
"""
from typing import Optional, Dict, Any


class AppError(Exception):
    """Base application error."""
    def __init__(self, message: str, code: str = "APP_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class TierRestrictionError(AppError):
    """Raised when user tries to perform action not allowed in their tier."""
    def __init__(self, action: str, tier: str, required_tier: str = "pro"):
        super().__init__(
            message=f"Action '{action}' requires {required_tier} tier. Current tier: {tier}",
            code="TIER_RESTRICTION",
            details={"action": action, "current_tier": tier, "required_tier": required_tier}
        )


class LLMError(AppError):
    """Raised when LLM call fails."""
    def __init__(self, message: str, model: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="LLM_ERROR",
            details={"model": model, **(details or {})}
        )


class RAGError(AppError):
    """Raised when RAG operation fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="RAG_ERROR",
            details=details or {}
        )


class ActionExecutionError(AppError):
    """Raised when action execution fails."""
    def __init__(self, message: str, action_type: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="ACTION_EXECUTION_ERROR",
            details={"action_type": action_type, **(details or {})}
        )


class ValidationError(AppError):
    """Raised when validation fails."""
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field": field, **(details or {})}
        )

