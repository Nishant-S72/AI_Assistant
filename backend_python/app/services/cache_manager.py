"""Cache manager for summaries, contact summaries, tags, badges, and related data."""
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import asyncio
import json

# In-memory cache stores
_summary_cache: Optional[Dict[str, Any]] = None
_summary_cache_timestamp: Optional[float] = None
_contact_summary_cache: Dict[str, Dict[str, Any]] = {}  # contact_id -> summary data
_category_summary_cache: Dict[str, Dict[str, Any]] = {}  # category -> summary data
_contact_tags_cache: Dict[str, List[str]] = {}  # contact_id -> tags list
_tags_cache_timestamp: Dict[str, float] = {}  # contact_id -> timestamp
_badges_cache: Optional[Dict[str, Any]] = None
_badges_cache_timestamp: Optional[float] = None

# Cache invalidation tracking
_cache_invalidation_keys: Dict[str, Any] = {
    "last_message_timestamp": None,
    "last_contact_update": None,
    "last_thread_created": None,
    "affected_contact_ids": set(),  # Track which contacts need cache refresh
    "affected_thread_ids": set(),  # Track which threads need cache refresh
}

# Refresh callbacks - functions to call when cache is invalidated
_refresh_callbacks: List[Callable] = []


def invalidate_cache(
    reason: str,
    contact_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    message_timestamp: Optional[datetime] = None,
    trigger_refresh: bool = True
):
    """
    Invalidate caches when new messages are added or conversations change.
    Automatically triggers refresh of summaries, tags, and badges.
    
    Args:
        reason: Reason for invalidation (e.g., "new_message", "new_conversation", "tag_updated")
        contact_id: Contact ID affected (optional)
        thread_id: Thread ID affected (optional)
        message_timestamp: Timestamp of the new message (optional)
        trigger_refresh: Whether to trigger automatic refresh (default: True)
    """
    global _summary_cache, _summary_cache_timestamp
    global _contact_summary_cache, _category_summary_cache
    global _contact_tags_cache, _tags_cache_timestamp
    global _badges_cache, _badges_cache_timestamp
    global _cache_invalidation_keys, _refresh_callbacks
    
    print(f"[Cache] Invalidating cache - Reason: {reason}, Contact: {contact_id}, Thread: {thread_id}")
    
    # Invalidate dashboard summary
    _summary_cache = None
    _summary_cache_timestamp = None
    
    # Invalidate badges cache
    _badges_cache = None
    _badges_cache_timestamp = None
    
    # Invalidate contact-specific summaries and tags
    if contact_id:
        if contact_id in _contact_summary_cache:
            del _contact_summary_cache[contact_id]
        if contact_id in _contact_tags_cache:
            del _contact_tags_cache[contact_id]
        if contact_id in _tags_cache_timestamp:
            del _tags_cache_timestamp[contact_id]
        _cache_invalidation_keys["affected_contact_ids"].add(contact_id)
    
    # Invalidate category summaries (they depend on overall data)
    _category_summary_cache.clear()
    
    # Update invalidation keys
    if message_timestamp:
        timestamp_ms = message_timestamp.timestamp() * 1000
        if _cache_invalidation_keys["last_message_timestamp"] is None or \
           timestamp_ms > _cache_invalidation_keys["last_message_timestamp"]:
            _cache_invalidation_keys["last_message_timestamp"] = timestamp_ms
    
    if thread_id:
        _cache_invalidation_keys["affected_thread_ids"].add(thread_id)
    
    if contact_id:
        _cache_invalidation_keys["last_contact_update"] = datetime.now().timestamp() * 1000
    
    print(f"[Cache] Cache invalidated. Affected contacts: {len(_cache_invalidation_keys['affected_contact_ids'])}, Affected threads: {len(_cache_invalidation_keys['affected_thread_ids'])}")
    
    # Trigger automatic refresh if enabled
    if trigger_refresh:
        _trigger_refresh(contact_id, thread_id, reason)


def get_summary_cache() -> Optional[Dict[str, Any]]:
    """Get cached dashboard summary if valid."""
    global _summary_cache, _summary_cache_timestamp
    
    if _summary_cache and _summary_cache_timestamp:
        cache_age = (datetime.now().timestamp() * 1000) - _summary_cache_timestamp
        # Cache is valid for 1 minute, but will be invalidated on new messages
        if cache_age < 60000:
            return _summary_cache
    
    return None


def set_summary_cache(data: Dict[str, Any]):
    """Set cached dashboard summary."""
    global _summary_cache, _summary_cache_timestamp
    _summary_cache = data
    _summary_cache_timestamp = datetime.now().timestamp() * 1000
    print(f"[Cache] Dashboard summary cached")


def get_contact_summary_cache(contact_id: str) -> Optional[Dict[str, Any]]:
    """Get cached contact summary if valid."""
    global _contact_summary_cache, _cache_invalidation_keys
    
    if contact_id in _contact_summary_cache:
        cache_data = _contact_summary_cache[contact_id]
        cache_age = (datetime.now().timestamp() * 1000) - cache_data.get("timestamp", 0)
        
        # Check if this contact was affected by recent changes
        if contact_id in _cache_invalidation_keys["affected_contact_ids"]:
            # Cache is invalid
            del _contact_summary_cache[contact_id]
            _cache_invalidation_keys["affected_contact_ids"].discard(contact_id)
            return None
        
        # Cache is valid for 1 minute
        if cache_age < 60000:
            return cache_data.get("data")
    
    return None


def set_contact_summary_cache(contact_id: str, data: Dict[str, Any]):
    """Set cached contact summary."""
    global _contact_summary_cache
    _contact_summary_cache[contact_id] = {
        "data": data,
        "timestamp": datetime.now().timestamp() * 1000
    }
    print(f"[Cache] Contact summary cached for {contact_id}")


def get_category_summary_cache(category: str) -> Optional[Dict[str, Any]]:
    """Get cached category summary if valid."""
    global _category_summary_cache
    
    if category in _category_summary_cache:
        cache_data = _category_summary_cache[category]
        cache_age = (datetime.now().timestamp() * 1000) - cache_data.get("timestamp", 0)
        
        # Category summaries are invalidated when any message changes
        # Check if there's a newer message timestamp
        global _cache_invalidation_keys
        if _cache_invalidation_keys.get("last_message_timestamp"):
            cache_timestamp = cache_data.get("timestamp", 0)
            if _cache_invalidation_keys["last_message_timestamp"] > cache_timestamp:
                # Cache is invalid
                del _category_summary_cache[category]
                return None
        
        # Cache is valid for 1 minute
        if cache_age < 60000:
            return cache_data.get("data")
    
    return None


def set_category_summary_cache(category: str, data: Dict[str, Any]):
    """Set cached category summary."""
    global _category_summary_cache, _cache_invalidation_keys
    _category_summary_cache[category] = {
        "data": data,
        "timestamp": datetime.now().timestamp() * 1000
    }
    print(f"[Cache] Category summary cached for {category}")


def get_affected_contacts() -> List[str]:
    """Get list of contact IDs that need cache refresh."""
    global _cache_invalidation_keys
    return list(_cache_invalidation_keys["affected_contact_ids"])


def get_affected_threads() -> List[str]:
    """Get list of thread IDs that need cache refresh."""
    global _cache_invalidation_keys
    return list(_cache_invalidation_keys["affected_thread_ids"])


def clear_affected_lists():
    """Clear the affected contacts and threads lists after refresh."""
    global _cache_invalidation_keys
    _cache_invalidation_keys["affected_contact_ids"].clear()
    _cache_invalidation_keys["affected_thread_ids"].clear()
    print(f"[Cache] Cleared affected contacts and threads lists")


def _trigger_refresh(contact_id: Optional[str] = None, thread_id: Optional[str] = None, reason: str = "unknown"):
    """Trigger automatic refresh of affected caches."""
    global _refresh_callbacks
    
    print(f"[Cache] Triggering automatic refresh - Reason: {reason}, Contact: {contact_id}, Thread: {thread_id}")
    
    # Import refresh service to trigger refresh
    try:
        from app.services.cache_refresh_service import refresh_affected_caches
        # Run refresh in background (don't await)
        asyncio.create_task(refresh_affected_caches(contact_id, thread_id, reason))
    except ImportError:
        # Refresh service not available yet, will be created
        print(f"[Cache] Refresh service not available yet")
    except Exception as e:
        print(f"[Cache] Error triggering refresh: {e}")


def get_contact_tags_cache(contact_id: str) -> Optional[List[str]]:
    """Get cached tags for a contact if valid."""
    global _contact_tags_cache, _tags_cache_timestamp, _cache_invalidation_keys
    
    if contact_id in _contact_tags_cache:
        # Check if this contact was affected by recent changes
        if contact_id in _cache_invalidation_keys["affected_contact_ids"]:
            # Cache is invalid
            del _contact_tags_cache[contact_id]
            if contact_id in _tags_cache_timestamp:
                del _tags_cache_timestamp[contact_id]
            return None
        
        # Check cache age
        cache_timestamp = _tags_cache_timestamp.get(contact_id, 0)
        cache_age = (datetime.now().timestamp() * 1000) - cache_timestamp
        if cache_age < 60000:  # Valid for 1 minute
            return _contact_tags_cache[contact_id]
    
    return None


def set_contact_tags_cache(contact_id: str, tags: List[str]):
    """Set cached tags for a contact."""
    global _contact_tags_cache, _tags_cache_timestamp
    _contact_tags_cache[contact_id] = tags
    _tags_cache_timestamp[contact_id] = datetime.now().timestamp() * 1000
    print(f"[Cache] Contact tags cached for {contact_id}: {tags}")


def get_badges_cache() -> Optional[Dict[str, Any]]:
    """Get cached badges/metrics if valid."""
    global _badges_cache, _badges_cache_timestamp
    
    if _badges_cache and _badges_cache_timestamp:
        cache_age = (datetime.now().timestamp() * 1000) - _badges_cache_timestamp
        # Cache is valid for 1 minute
        if cache_age < 60000:
            return _badges_cache
    
    return None


def set_badges_cache(data: Dict[str, Any]):
    """Set cached badges/metrics."""
    global _badges_cache, _badges_cache_timestamp
    _badges_cache = data
    _badges_cache_timestamp = datetime.now().timestamp() * 1000
    print(f"[Cache] Badges cached")

