"""Function registry for LLM tool calling."""
from typing import Dict, Callable, Any, List
import json


class ToolRegistry:
    """Registry for LLM-callable functions."""
    
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._handlers: Dict[str, Callable] = {}
    
    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable,
    ):
        """
        Register a tool.
        
        Args:
            name: Function name
            description: Function description
            parameters: JSON Schema for parameters
            handler: Async function handler
        """
        self._tools[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        }
        self._handlers[name] = handler
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get list of tool definitions for LLM."""
        return list(self._tools.values())
    
    async def call(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a registered tool handler."""
        if name not in self._handlers:
            raise ValueError(f"Tool '{name}' not found")
        handler = self._handlers[name]
        return await handler(**arguments)


# Global registry instance
_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get global tool registry."""
    return _registry


# Register sample tools
async def send_email_stub(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Send email (stub implementation)."""
    # TODO: Implement actual email sending
    return {
        "success": True,
        "message_id": f"stub-{to}-{subject[:10]}",
        "to": to,
        "subject": subject,
    }


async def get_calendar_events(range_start: str, range_end: str) -> List[Dict[str, Any]]:
    """Get calendar events in date range."""
    # TODO: Implement actual calendar fetch
    return [
        {
            "id": "stub-1",
            "title": "Sample Event",
            "start": range_start,
            "end": range_end,
        }
    ]


# Initialize registry with sample tools
_registry.register(
    name="send_email",
    description="Send an email to a recipient",
    parameters={
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address"},
            "subject": {"type": "string", "description": "Email subject"},
            "body": {"type": "string", "description": "Email body"},
        },
        "required": ["to", "subject", "body"],
    },
    handler=send_email_stub,
)

_registry.register(
    name="get_calendar_events",
    description="Get calendar events in a date range",
    parameters={
        "type": "object",
        "properties": {
            "range_start": {"type": "string", "description": "Start date (ISO format)"},
            "range_end": {"type": "string", "description": "End date (ISO format)"},
        },
        "required": ["range_start", "range_end"],
    },
    handler=get_calendar_events,
)

