"""SSE (Server-Sent Events) manager for in-app notifications."""
from typing import Dict, Any, Set
import asyncio

# Store active SSE connections per user
_sse_connections: Dict[str, Set[asyncio.Queue]] = {}


def register_sse_connection(user_id: str, queue: asyncio.Queue) -> None:
    """Register an SSE connection for a user."""
    if user_id not in _sse_connections:
        _sse_connections[user_id] = set()
    _sse_connections[user_id].add(queue)


def unregister_sse_connection(user_id: str, queue: asyncio.Queue) -> None:
    """Unregister an SSE connection."""
    if user_id in _sse_connections:
        _sse_connections[user_id].discard(queue)
        if not _sse_connections[user_id]:
            del _sse_connections[user_id]


async def send_sse_notification(user_id: str, notification: Dict[str, Any]) -> None:
    """
    Send notification to all active SSE connections for a user.
    
    Args:
        user_id: User ID
        notification: Notification data
    """
    if user_id not in _sse_connections:
        return
    
    for queue in _sse_connections[user_id]:
        try:
            await queue.put(notification)
        except Exception as e:
            print(f"[SSE] Error sending notification to {user_id}: {e}")


