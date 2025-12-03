"""Fallback LLM wrapper with retry logic."""
from typing import Callable, Any, Optional
from app.clients.llm import generate_chat_completion, LLMRequestOptions, LLMMessage
import asyncio
import logging

logger = logging.getLogger(__name__)


async def call_with_fallback(
    primary_model: str,
    fallback_model: str,
    request_options: LLMRequestOptions,
    max_retries: int = 1,
) -> Any:
    """
    Call LLM with fallback on failure.
    
    Args:
        primary_model: Primary model to try first
        fallback_model: Fallback model if primary fails
        request_options: LLM request options
        max_retries: Maximum retries with primary before fallback
    
    Returns:
        LLM response from successful call
    
    Raises:
        Exception if both models fail
    """
    # Try primary model first
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Attempting primary model: {primary_model} (attempt {attempt + 1})")
            request_options.model = primary_model
            response = await asyncio.wait_for(
                generate_chat_completion(request_options),
                timeout=30.0,  # 30 second timeout
            )
            logger.info(f"Primary model succeeded: {primary_model}")
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Primary model timeout: {primary_model} (attempt {attempt + 1})")
            if attempt < max_retries:
                continue
        except Exception as e:
            logger.warning(f"Primary model error: {primary_model} - {str(e)} (attempt {attempt + 1})")
            if attempt < max_retries:
                continue
    
    # Primary failed, try fallback
    try:
        logger.info(f"Attempting fallback model: {fallback_model}")
        request_options.model = fallback_model
        response = await asyncio.wait_for(
            generate_chat_completion(request_options),
            timeout=30.0,
        )
        logger.info(f"Fallback model succeeded: {fallback_model}")
        return response
    except Exception as e:
        logger.error(f"Fallback model also failed: {fallback_model} - {str(e)}")
        raise Exception(f"Both primary ({primary_model}) and fallback ({fallback_model}) models failed: {str(e)}")

