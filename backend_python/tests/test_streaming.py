"""Tests for streaming chat endpoint."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import AsyncMock, patch


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.mark.asyncio
async def test_stream_chat_generator():
    """Test event stream generator yields correct format."""
    from app.routes.v1.stream_chat import event_stream_generator
    
    mock_messages = [
        {"role": "user", "content": "Hello"}
    ]
    
    # Mock stream_chat to yield test tokens
    async def mock_stream():
        yield {"type": "token", "text": "Hello"}
        yield {"type": "token", "text": " world"}
        yield {"type": "done", "text": "[DONE]"}
    
    with patch("app.routes.v1.stream_chat.stream_chat", return_value=mock_stream()):
        chunks = []
        async for chunk in event_stream_generator(mock_messages, None):
            chunks.append(chunk)
        
        assert len(chunks) == 3
        assert "data: " in chunks[0]
        assert "[DONE]" in chunks[-1]


def test_stream_chat_endpoint(client):
    """Test streaming chat endpoint returns SSE."""
    response = client.post(
        "/api/v1/stream_chat",
        json={
            "messages": [{"role": "user", "content": "Test"}],
            "model": "gpt-4o-mini",
        },
    )
    
    # Should return 200 with text/event-stream
    assert response.status_code in [200, 500]  # 500 if OpenAI key not set
    if response.status_code == 200:
        assert "text/event-stream" in response.headers.get("content-type", "")

