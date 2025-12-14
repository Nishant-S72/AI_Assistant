"""
Regression tests for chat bubble - ensure non-scheduling features still work.

These tests verify that removing the chat-bubble scheduler did not break:
- General chat functionality
- Reply suggestion generation
- Policy queries
- RAG chat
- Inbox assistance
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)


def test_general_chat_still_works():
    """Test that general chat still works after removing scheduler."""
    response = client.post(
        "/api/chat",
        json={
            "userMessage": "Hello, how are you?",
            "threadId": "test_thread_1",
            "tone": "warm",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "text" in data or "response" in data
    assert data.get("intent") != "action_intent" or "calendar" not in data.get("text", "").lower()


def test_policy_query_still_works():
    """Test that policy queries still work."""
    response = client.post(
        "/api/chat",
        json={
            "userMessage": "What is our refund policy?",
            "threadId": "test_thread_2",
            "tone": "formal",
        },
    )
    assert response.status_code == 200
    data = response.json()
    # Should handle policy intent
    assert "text" in data or "response" in data


def test_reply_suggestion_still_works():
    """Test that reply suggestion generation still works."""
    # This would typically be tested via the messages endpoint
    # For now, verify the chat endpoint doesn't break
    response = client.post(
        "/api/chat",
        json={
            "userMessage": "Can you help me draft a reply?",
            "threadId": "test_thread_3",
            "tone": "warm",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "text" in data or "response" in data


def test_scheduling_request_redirects():
    """Test that scheduling requests are redirected to use scheduler interface."""
    response = client.post(
        "/api/chat",
        json={
            "userMessage": "Schedule a meeting tomorrow at 2pm",
            "threadId": "test_thread_4",
            "tone": "warm",
        },
    )
    assert response.status_code == 200
    data = response.json()
    # Should not create calendar event, should suggest using scheduler
    assert "text" in data or "response" in data
    # Should not have action_result with eventId
    assert "action_result" not in data or not data.get("action_result", {}).get("eventId")


def test_action_intent_no_longer_creates_calendar_events():
    """Test that action_intent no longer creates calendar events."""
    response = client.post(
        "/api/chat",
        json={
            "userMessage": "Schedule a meeting",
            "threadId": "test_thread_5",
            "tone": "warm",
        },
    )
    assert response.status_code == 200
    data = response.json()
    # Should not have calendar event creation
    if "action_result" in data:
        assert "eventId" not in data["action_result"] or data["action_result"].get("eventId") is None


def test_chat_bubble_renders_conversation():
    """Test that chat bubble can still display conversations."""
    # First message
    response1 = client.post(
        "/api/chat",
        json={
            "userMessage": "Hi there",
            "threadId": "test_thread_6",
            "tone": "warm",
        },
    )
    assert response1.status_code == 200
    
    # Follow-up message
    response2 = client.post(
        "/api/chat",
        json={
            "userMessage": "Tell me about the inbox",
            "threadId": "test_thread_6",
            "tone": "warm",
        },
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert "text" in data2 or "response" in data2


def test_non_scheduling_action_keywords_still_work():
    """Test that non-scheduling action keywords don't break."""
    response = client.post(
        "/api/chat",
        json={
            "userMessage": "Create a task for tomorrow",
            "threadId": "test_thread_7",
            "tone": "warm",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "text" in data or "response" in data


def test_rag_chat_still_works():
    """Test that RAG-enabled chat still works."""
    response = client.post(
        "/api/chat",
        json={
            "userMessage": "What information do you have about our products?",
            "threadId": "test_thread_8",
            "tone": "warm",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "text" in data or "response" in data


def test_intent_classifier_no_longer_detects_scheduling():
    """Test that intent classifier no longer classifies scheduling as action_intent."""
    from app.policy.intent_classifier import classify_intent
    
    # Test that scheduling keywords don't trigger action_intent
    result = classify_intent("Schedule a meeting tomorrow")
    # Should be general_intent or policy_intent, not action_intent
    assert result["intent"] != "action_intent" or result.get("confidence", 0) < 0.5


def test_handle_action_intent_no_calendar_logic():
    """Test that handle_action_intent no longer has calendar creation logic."""
    from app.routes.chat import handle_action_intent
    import asyncio
    
    # This should not create calendar events
    result = asyncio.run(handle_action_intent(
        "Schedule a meeting tomorrow at 2pm",
        "test_thread",
        "warm",
        {"intent": "action_intent", "confidence": 0.9}
    ))
    
    # Should not have action_result with eventId
    assert "action_result" not in result or not result.get("action_result", {}).get("eventId")
    # Should suggest using scheduler
    assert "scheduler" in result.get("text", "").lower() or "calendar" in result.get("text", "").lower()

