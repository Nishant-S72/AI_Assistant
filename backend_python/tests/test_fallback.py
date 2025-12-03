"""Tests for fallback LLM wrapper."""
import pytest
from app.clients.llm.fallback_wrapper import call_with_fallback
from app.clients.llm import LLMRequestOptions, LLMMessage
from unittest.mock import AsyncMock, patch
import asyncio


@pytest.mark.asyncio
async def test_fallback_on_primary_failure():
    """Test fallback is used when primary fails."""
    primary_model = "gpt-4"
    fallback_model = "gpt-4o-mini"
    
    request_options = LLMRequestOptions(
        model=primary_model,
        messages=[LLMMessage("user", "Test")],
    )
    
    # Mock primary failure, fallback success
    mock_response = AsyncMock()
    mock_response.content = "Fallback response"
    
    with patch("app.clients.llm.fallback_wrapper.generate_chat_completion") as mock_llm:
        # Primary fails
        mock_llm.side_effect = [
            Exception("Primary failed"),
            mock_response,  # Fallback succeeds
        ]
        
        result = await call_with_fallback(
            primary_model,
            fallback_model,
            request_options,
        )
        
        assert result.content == "Fallback response"
        assert mock_llm.call_count == 2  # Primary + fallback

