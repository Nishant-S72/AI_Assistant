"""Tests for conversation memory and summarization."""
import pytest
from app.services.conversation_store import ConversationStore, get_conversation_store
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_conversation_store_add_message():
    """Test adding messages to conversation."""
    store = ConversationStore()
    conv_id = "test-conv-1"
    
    store.add_message(conv_id, "user", "Hello")
    store.add_message(conv_id, "assistant", "Hi there")
    
    conv = store.get_conversation(conv_id)
    assert conv is not None
    assert len(conv["messages"]) == 2


@pytest.mark.asyncio
async def test_auto_summarization():
    """Test auto-summarization when threshold exceeded."""
    store = ConversationStore()
    conv_id = "test-conv-2"
    
    # Add more than MAX_MESSAGES
    for i in range(35):
        store.add_message(conv_id, "user", f"Message {i}")
    
    # Mock summarization
    with patch.object(store, "_summarize_messages", return_value="Summary of old messages"):
        await store._auto_summarize(conv_id)
        
        conv = store.get_conversation(conv_id)
        # Should have summary + recent messages
        assert conv["summary"] is not None
        assert len(conv["messages"]) < 35


@pytest.mark.asyncio
async def test_regenerate_summary():
    """Test force regeneration of summary."""
    store = get_conversation_store()
    conv_id = "test-conv-3"
    
    store.add_message(conv_id, "user", "Message 1")
    store.add_message(conv_id, "assistant", "Response 1")
    
    with patch.object(store, "_summarize_messages", return_value="New summary"):
        summary = await store.regenerate_summary(conv_id)
        assert summary == "New summary"
        
        conv = store.get_conversation(conv_id)
        assert conv["summary"] == "New summary"

