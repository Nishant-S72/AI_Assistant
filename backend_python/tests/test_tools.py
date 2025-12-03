"""Tests for function calling tools."""
import pytest
from app.tools.registry import ToolRegistry, get_registry


@pytest.mark.asyncio
async def test_tool_registry():
    """Test tool registry registration and calling."""
    registry = ToolRegistry()
    
    # Register a test tool
    async def test_handler(arg1: str, arg2: int) -> dict:
        return {"result": f"{arg1}-{arg2}"}
    
    registry.register(
        name="test_tool",
        description="Test tool",
        parameters={
            "type": "object",
            "properties": {
                "arg1": {"type": "string"},
                "arg2": {"type": "integer"},
            },
            "required": ["arg1", "arg2"],
        },
        handler=test_handler,
    )
    
    # Test getting tools
    tools = registry.get_tools()
    assert len(tools) == 1
    assert tools[0]["function"]["name"] == "test_tool"
    
    # Test calling tool
    result = await registry.call("test_tool", {"arg1": "hello", "arg2": 42})
    assert result["result"] == "hello-42"


@pytest.mark.asyncio
async def test_sample_tools():
    """Test sample tools (send_email, get_calendar_events)."""
    registry = get_registry()
    
    # Test send_email
    result = await registry.call(
        "send_email",
        {"to": "test@example.com", "subject": "Test", "body": "Body"}
    )
    assert result["success"] is True
    assert "message_id" in result
    
    # Test get_calendar_events
    result = await registry.call(
        "get_calendar_events",
        {"range_start": "2024-01-01", "range_end": "2024-01-31"}
    )
    assert isinstance(result, list)
    assert len(result) > 0

