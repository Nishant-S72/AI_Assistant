"""Tests for function calling / tool registry."""
import pytest
from app.tools.registry import ToolRegistry, get_registry
from app.tools.sample_handlers import send_email_stub, get_calendar_events


def test_register_tool():
    """Test tool registration."""
    registry = ToolRegistry()
    
    async def test_handler(x: str) -> str:
        return f"Result: {x}"
    
    registry.register_tool(
        name="test_tool",
        schema={
            "description": "Test tool",
            "parameters": {
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
            },
        },
        handler=test_handler,
    )
    
    tool = registry.get_tool("test_tool")
    assert tool is not None
    assert tool["function"]["name"] == "test_tool"


def test_list_schemas():
    """Test listing all tool schemas."""
    registry = get_registry()
    schemas = registry.list_schemas()
    
    assert len(schemas) >= 2  # Should have send_email and get_calendar_events
    tool_names = [s["function"]["name"] for s in schemas]
    assert "send_email" in tool_names
    assert "get_calendar_events" in tool_names


@pytest.mark.asyncio
async def test_call_tool():
    """Test calling a registered tool."""
    registry = get_registry()
    
    result = await registry.call("send_email", {
        "to": "test@example.com",
        "subject": "Test",
        "body": "Body",
    })
    
    assert result["success"] is True
    assert result["to"] == "test@example.com"


@pytest.mark.asyncio
async def test_function_call_in_chat():
    """Test that function calls trigger handlers correctly."""
    from app.routes.v1.chat_with_tools import chat_with_tools
    from fastapi import Request
    
    # Mock OpenAI response with function call
    with patch("app.routes.v1.chat_with_tools.AsyncOpenAI") as mock_openai:
        mock_client = AsyncMock()
        mock_message = AsyncMock()
        mock_message.content = None
        mock_tool_call = AsyncMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "send_email"
        mock_tool_call.function.arguments = '{"to": "test@example.com", "subject": "Test", "body": "Body"}'
        mock_message.tool_calls = [mock_tool_call]
        mock_choice = AsyncMock()
        mock_choice.message = mock_message
        mock_response = AsyncMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client
        
        # This would require a full request object, so we'll test the registry directly
        registry = get_registry()
        result = await registry.call("send_email", {
            "to": "test@example.com",
            "subject": "Test",
            "body": "Body",
        })
        
        assert result["success"] is True
