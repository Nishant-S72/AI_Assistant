"""Tests for SSE streaming endpoint."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import AsyncMock, patch
import json

client = TestClient(app)


@pytest.mark.asyncio
async def test_stream_chat_generator():
    """Test that stream_chat generator yields correct format."""
    from app.clients.llm.adapter import stream_chat
    
    # Mock OpenAI stream
    mock_chunk = AsyncMock()
    mock_chunk.choices = [AsyncMock()]
    mock_chunk.choices[0].delta = AsyncMock()
    mock_chunk.choices[0].delta.content = "Hello"
    
    with patch("app.clients.llm.adapter.AsyncOpenAI") as mock_openai:
        mock_client = AsyncMock()
        mock_stream = AsyncMock()
        mock_stream.__aiter__ = AsyncMock(return_value=iter([mock_chunk]))
        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream)
        mock_openai.return_value = mock_client
        
        chunks = []
        async for chunk in stream_chat([{"role": "user", "content": "Hi"}]):
            chunks.append(chunk)
        
        assert len(chunks) >= 1
        assert chunks[0]["type"] == "token"
        assert chunks[0]["text"] == "Hello"
        # Should end with done
        assert chunks[-1]["type"] == "done"


def test_stream_chat_endpoint():
    """Test SSE endpoint returns correct format."""
    with patch("app.routes.v1.stream_chat.stream_chat") as mock_stream:
        async def mock_generator():
            yield {"type": "token", "text": "Hello"}
            yield {"type": "done"}
        
        mock_stream.return_value = mock_generator()
        
        response = client.post(
            "/api/v1/stream_chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        
        # Parse SSE
        lines = response.text.strip().split("\n")
        assert any("data:" in line for line in lines)
