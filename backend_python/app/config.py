"""Application configuration and feature flags."""
import os


def is_scheduler_enabled() -> bool:
    """
    Check if new scheduler is enabled.
    
    Returns:
        True if NEW_SCHEDULER_ENABLED is set to 'true', False otherwise
    """
    return os.getenv("NEW_SCHEDULER_ENABLED", "false").lower() == "true"


def get_feature_flags() -> dict:
    """
    Get all feature flags.
    
    Returns:
        Dict of feature flag names to boolean values
    """
    return {
        "new_scheduler_enabled": is_scheduler_enabled(),
        "use_ollama": os.getenv("USE_OLLAMA", "false").lower() == "true",
        "rag_enabled": os.getenv("RAG_ENABLED", "true").lower() == "true",
    }

