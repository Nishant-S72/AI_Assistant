"""
Deduplication utilities for threads, contacts, and tasks.
"""
from typing import Dict, Any, List, Optional
import re
from difflib import SequenceMatcher


def normalize_thread_id(
    subject: Optional[str] = None,
    participants: Optional[List[str]] = None,
    time_window_hours: int = 24,
) -> str:
    """
    Normalize thread ID by cleaning subject and considering participants.
    
    Args:
        subject: Email subject line
        participants: List of participant emails
        time_window_hours: Time window for considering threads as related
    
    Returns:
        Normalized thread identifier
    """
    # Clean subject
    if subject:
        # Remove common prefixes
        subject = re.sub(r'^(Re:|Fwd?:|RE:|FW:)\s*', '', subject, flags=re.IGNORECASE)
        # Normalize whitespace
        subject = ' '.join(subject.split())
        # Lowercase for comparison
        subject = subject.lower()
    else:
        subject = ""
    
    # Normalize participants
    normalized_participants = []
    if participants:
        for email in participants:
            if email:
                normalized_participants.append(email.lower().strip())
        normalized_participants.sort()
    
    # Create deterministic identifier
    parts = [subject] + normalized_participants
    return "|".join(parts)


def similarity_score(text1: str, text2: str) -> float:
    """
    Calculate similarity score between two texts (0.0 to 1.0).
    
    Uses SequenceMatcher for fuzzy matching.
    """
    if not text1 or not text2:
        return 0.0
    
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def is_duplicate_task(
    new_task: Dict[str, Any],
    existing_tasks: List[Dict[str, Any]],
    title_similarity_threshold: float = 0.85,
) -> bool:
    """
    Check if a task is a duplicate of an existing task.
    
    Args:
        new_task: New task to check
        existing_tasks: List of existing tasks
        title_similarity_threshold: Minimum similarity to consider duplicate
    
    Returns:
        True if duplicate found
    """
    new_title = new_task.get("title", "").lower().strip()
    new_thread_id = new_task.get("thread_id")
    new_contact_id = new_task.get("contact_id")
    
    if not new_title:
        return False
    
    for existing in existing_tasks:
        existing_title = existing.get("title", "").lower().strip()
        existing_thread_id = existing.get("thread_id")
        existing_contact_id = existing.get("contact_id")
        
        # Exact match on thread_id and contact_id
        if new_thread_id and existing_thread_id and new_thread_id == existing_thread_id:
            if new_contact_id and existing_contact_id and new_contact_id == existing_contact_id:
                return True
        
        # Similarity check on title
        if existing_title:
            similarity = similarity_score(new_title, existing_title)
            if similarity >= title_similarity_threshold:
                # Additional check: same contact or thread
                if (new_contact_id and existing_contact_id and new_contact_id == existing_contact_id) or \
                   (new_thread_id and existing_thread_id and new_thread_id == existing_thread_id):
                    return True
    
    return False


def merge_contacts(
    contact1: Dict[str, Any],
    contact2: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Merge two contact records, keeping the most complete information.
    
    Strategy:
    - Same email → same contact
    - Multiple emails for same person → link to primary ID
    
    Returns:
        Merged contact dictionary
    """
    # Primary contact is the one with more complete information
    primary = contact1 if len(str(contact1)) > len(str(contact2)) else contact2
    secondary = contact2 if primary is contact1 else contact1
    
    merged = primary.copy()
    
    # Merge emails (keep all unique emails)
    emails = set()
    if primary.get("email"):
        emails.add(primary["email"].lower())
    if secondary.get("email"):
        emails.add(secondary["email"].lower())
    
    if emails:
        merged["email"] = primary.get("email")  # Keep primary email as main
        if len(emails) > 1:
            merged["alternate_emails"] = list(emails - {primary.get("email", "").lower()})
    
    # Merge names (prefer non-empty)
    if not merged.get("name") and secondary.get("name"):
        merged["name"] = secondary["name"]
    
    # Merge companies (prefer non-empty)
    if not merged.get("company") and secondary.get("company"):
        merged["company"] = secondary["company"]
    
    # Merge tags (union of both)
    tags1 = set(primary.get("tags", []) or [])
    tags2 = set(secondary.get("tags", []) or [])
    merged["tags"] = list(tags1 | tags2)
    
    return merged

