"""Tests for conversation memory and summarization."""
import pytest
from app.services.conversation_store import ConversationStore
from app.conversation.summarizer import summarize_messages


@pytest.mark.asyncio
async def test_conversation_store_add_message():
    """Test adding messages to conversation store."""
    store = ConversationStore()
    store.add_message("conv1", "user", "Hello")
    store.add_message("conv1", "assistant", "Hi there!")
    
    conv = store.get_conversation("conv1")
    assert conv is not None
    assert len(conv["messages"]) == 2
    assert conv["messages"][0]["role"] == "user"
    assert conv["messages"][1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_auto_summarization():
    """Test that conversations are auto-summarized when threshold exceeded."""
    store = ConversationStore()
    
    # Add more than MAX_MESSAGES
    for i in range(store.MAX_MESSAGES + 5):
        store.add_message("conv2", "user", f"Message {i}")
    
    # Trigger auto-summarization
    await store._auto_summarize("conv2")
    
    conv = store.get_conversation("conv2")
    # Should have summary placeholder + recent messages
    assert conv["summary"] is not None
    assert len(conv["messages"]) < store.MAX_MESSAGES + 5


@pytest.mark.asyncio
async def test_summarize_messages():
    """Test message summarization."""
    messages = [
        {"role": "user", "content": "What is the capital of France?"},
        {"role": "assistant", "content": "The capital of France is Paris."},
        {"role": "user", "content": "What about Germany?"},
        {"role": "assistant", "content": "The capital of Germany is Berlin."},
    ]
    
    # Mock LLM call
    with patch("app.clients.llm.adapter.summarize") as mock_summarize:
        mock_summarize.return_value = "User asked about capitals of France and Germany."
        
        summary = await summarize_messages(messages)
        assert "France" in summary or "Germany" in summary or "capitals" in summary.lower()


@pytest.mark.asyncio
async def test_regenerate_summary():
    """Test summary regeneration endpoint."""
    store = ConversationStore()
    store.add_message("conv3", "user", "Hello")
    store.add_message("conv3", "assistant", "Hi!")
    
    with patch("app.conversation.summarizer.summarize_messages") as mock_summarize:
        mock_summarize.return_value = "Test summary"
        
        summary = await store.regenerate_summary("conv3")
        assert summary == "Test summary"
        
        conv = store.get_conversation("conv3")
        assert conv["summary"] == "Test summary"


