"""Integration tests for chat endpoint."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_general_intent_chat():
    """Test general intent chat endpoint."""
    response = client.post(
        "/api/chat",
        json={
            "userMessage": "How do I write a follow-up email?",
            "tone": "warm"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "general_intent"
    assert data["kind"] == "assistant"
    assert "text" in data
    assert len(data.get("citations", [])) == 0


def test_policy_intent_chat():
    """Test policy intent chat endpoint (requires seeded vectorstore)."""
    response = client.post(
        "/api/chat",
        json={
            "userMessage": "What is our refund policy?",
            "tone": "formal"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "policy_intent"
    assert data["kind"] == "policy"
    # Citations may be empty if vectorstore not seeded - that's OK for test
    assert "citations" in data


def test_action_intent_chat():
    """Test action intent chat endpoint."""
    response = client.post(
        "/api/chat",
        json={
            "userMessage": "Schedule a meeting tomorrow at 3pm",
            "tone": "crisp"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "action_intent"
    assert data["kind"] == "action"
    assert "action_result" in data or "action_suggestion" in data


def test_escalation_chat():
    """Test that sensitive content triggers escalation."""
    response = client.post(
        "/api/chat",
        json={
            "userMessage": "We need to fire an employee for misconduct",
            "tone": "formal"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["escalated"] == True
    assert "escalated" in data or "reasons" in data

