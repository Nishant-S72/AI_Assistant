"""Function registry for LLM tool calling."""
from typing import Dict, Callable, Any, List, Optional
import json


class ToolRegistry:
    """Registry for LLM-callable functions."""
    
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._handlers: Dict[str, Callable] = {}
    
    def register_tool(
        self,
        name: str,
        schema: Dict[str, Any],
        handler: Callable,
    ):
        """
        Register a tool.
        
        Args:
            name: Function name
            schema: JSON Schema for function (must include 'description' and 'parameters')
            handler: Async function handler
        """
        description = schema.get("description", "")
        parameters = schema.get("parameters", {})
        
        self._tools[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        }
        self._handlers[name] = handler
    
    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Get tool definition by name."""
        return self._tools.get(name)
    
    def list_schemas(self) -> List[Dict[str, Any]]:
        """List all tool schemas."""
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


# Import sample handlers
from .sample_handlers import send_email_stub, get_calendar_events


# Initialize registry with sample tools
_registry.register_tool(
    name="send_email",
    schema={
        "description": "Send an email to a recipient",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    handler=send_email_stub,
)

_registry.register_tool(
    name="get_calendar_events",
    schema={
        "description": "Get calendar events in a date range",
        "parameters": {
            "type": "object",
            "properties": {
                "range_start": {"type": "string", "description": "Start date (ISO format)"},
                "range_end": {"type": "string", "description": "End date (ISO format)"},
            },
            "required": ["range_start", "range_end"],
        },
    },
    handler=get_calendar_events,
)

