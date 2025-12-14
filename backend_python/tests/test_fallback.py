"""Tests for fallback LLM logic."""
import pytest
from app.clients.llm.fallback_wrapper import call_with_fallback
from app.clients.llm import LLMRequestOptions, LLMMessage, LLMResponse
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_fallback_on_primary_failure():
    """Test that fallback is used when primary fails."""
    # Mock primary failure, fallback success
    with patch("app.clients.llm.fallback_wrapper.generate_chat_completion") as mock_llm:
        # First call fails (primary)
        mock_llm.side_effect = [
            Exception("Primary failed"),
            LLMResponse(content="Fallback response", model="fallback-model"),
        ]
        
        # Should retry with fallback
        response = await call_with_fallback(
            primary_model="primary-model",
            fallback_model="fallback-model",
            request_options=LLMRequestOptions(
                model="primary-model",
                messages=[LLMMessage("user", "Test")],
            ),
        )
        
        assert response.content == "Fallback response"
        assert mock_llm.call_count == 2  # Primary + fallback


@pytest.mark.asyncio
async def test_primary_success_no_fallback():
    """Test that fallback is not used when primary succeeds."""
    with patch("app.clients.llm.fallback_wrapper.generate_chat_completion") as mock_llm:
        mock_llm.return_value = LLMResponse(content="Primary response", model="primary-model")
        
        response = await call_with_fallback(
            primary_model="primary-model",
            fallback_model="fallback-model",
            request_options=LLMRequestOptions(
                model="primary-model",
                messages=[LLMMessage("user", "Test")],
            ),
        )
        
        assert response.content == "Primary response"
        assert mock_llm.call_count == 1  # Only primary called


@pytest.mark.asyncio
async def test_fallback_on_timeout():
    """Test that timeout triggers fallback."""
    import asyncio
    
    async def slow_llm(*args, **kwargs):
        await asyncio.sleep(35)  # Longer than timeout
        return LLMResponse(content="Too slow", model="primary")
    
    with patch("app.clients.llm.fallback_wrapper.generate_chat_completion", side_effect=slow_llm) as mock_llm:
        # Mock fallback to succeed quickly
        async def fast_fallback(*args, **kwargs):
            if args[0].model == "fallback-model":
                return LLMResponse(content="Fast fallback", model="fallback-model")
            await asyncio.sleep(35)
            raise asyncio.TimeoutError()
        
        mock_llm.side_effect = fast_fallback
        
        # This will timeout on primary and use fallback
        response = await call_with_fallback(
            primary_model="primary-model",
            fallback_model="fallback-model",
            request_options=LLMRequestOptions(
                model="primary-model",
                messages=[LLMMessage("user", "Test")],
            ),
        )
        
        # Should get fallback response
        assert "fallback" in response.content.lower() or response.model == "fallback-model"
