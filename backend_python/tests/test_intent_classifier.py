"""Tests for intent classifier."""
import pytest
import asyncio
from app.policy.intent_classifier import classify_intent_async, classify_intent_sync


def test_greeting_intent():
    """Test that greetings are classified as general_intent."""
    result = classify_intent_sync("Hi")
    assert result["intent"] == "general_intent"
    assert result["confidence"] >= 0.9


def test_policy_intent():
    """Test that policy questions are classified as policy_intent."""
    result = classify_intent_sync("What is our refund policy?")
    assert result["intent"] == "policy_intent"
    assert result["confidence"] >= 0.8


def test_action_intent_keywords():
    """Test that scheduling requests are classified as action_intent."""
    result = classify_intent_sync("Schedule a meeting tomorrow at 3pm")
    assert result["intent"] == "action_intent"
    assert result["confidence"] >= 0.8


def test_action_intent_with_email():
    """Test action intent with email address."""
    result = classify_intent_sync("Schedule a call with jane@example.com next Thursday")
    assert result["intent"] == "action_intent"


@pytest.mark.asyncio
async def test_llm_fallback_ambiguous():
    """Test that ambiguous queries use LLM fallback."""
    # This query is ambiguous - could be policy or action
    result = await classify_intent_async("What should I do about refunds?")
    
    # Should return one of the valid intents
    assert result["intent"] in ["policy_intent", "action_intent", "general_intent"]
    assert 0.0 <= result["confidence"] <= 1.0
    assert "method" in result


def test_action_time_patterns():
    """Test various time patterns trigger action intent."""
    test_cases = [
        "Schedule meeting tomorrow",
        "Book appointment next Monday",
        "Add event at 3pm",
        "Create meeting on Thursday",
    ]
    
    for test_case in test_cases:
        result = classify_intent_sync(test_case)
        assert result["intent"] == "action_intent", f"Failed for: {test_case}"


def test_policy_keywords():
    """Test various policy keywords trigger policy intent."""
    test_cases = [
        "What does our policy say?",
        "According to the guidelines",
        "What are the rules for",
        "Tell me about our procedures",
    ]
    
    for test_case in test_cases:
        result = classify_intent_sync(test_case)
        assert result["intent"] == "policy_intent", f"Failed for: {test_case}"

