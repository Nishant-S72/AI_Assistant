"""Google Gemini LLM adapter with async httpx for direct API calls."""
import os
import asyncio
import json
from typing import Optional
import httpx
from .openai_adapter import LLMMessage, LLMOptions, LLMResponse


async def generate_with_gemini(options: LLMOptions) -> LLMResponse:
    """Generate completion using Google Gemini API with direct httpx calls.
    
    Uses direct HTTP calls instead of SDK to avoid hanging issues.
    Reference: https://ai.google.dev/gemini-api/docs/quickstart
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not configured")
    
    # Convert messages to Gemini format
    system_prompt = None
    user_messages = []
    
    for msg in options.messages:
        if msg.role == "system":
            system_prompt = msg.content
        elif msg.role == "user":
            user_messages.append(msg.content)
        elif msg.role == "assistant":
            # Skip assistant messages for now
            pass
    
    # Combine system prompt with user message
    if system_prompt and user_messages:
        prompt = f"{system_prompt}\n\n{user_messages[0]}"
        if len(user_messages) > 1:
            prompt += "\n\n" + "\n\n".join(user_messages[1:])
    elif user_messages:
        prompt = "\n\n".join(user_messages)
    else:
        prompt = ""
    
    if not prompt:
        raise ValueError("No user message found in options.messages")
    
    # Get model name (default to gemini-2.5-flash - fastest model)
    model_name = options.model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # No timeout - let it run as long as needed
    # Use async httpx directly (much faster than SDK)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    params = {"key": api_key}
    
    # Build request body
    request_body = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    # Add generation config if needed (only temperature, no token limits unless explicitly set)
    if options.temperature is not None or (options.max_tokens and options.max_tokens > 0):
        gen_config = {}
        # Only set maxOutputTokens if explicitly provided and > 0 (no default limits)
        if options.max_tokens and options.max_tokens > 0:
            gen_config["maxOutputTokens"] = options.max_tokens
        if options.temperature is not None:
            gen_config["temperature"] = options.temperature
        if gen_config:
            request_body["generationConfig"] = gen_config
    
    # Retry logic for rate limiting (429 errors)
    max_retries = 3
    base_delay = 2.0  # Start with 2 seconds
    
    for attempt in range(max_retries):
        try:
            # Use async httpx directly - no timeout, no limits!
            async with httpx.AsyncClient(timeout=None) as client:
                response = await client.post(url, params=params, json=request_body)
                
                # Handle 429 rate limit errors with retry
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        # Exponential backoff: 2s, 4s, 8s
                        delay = base_delay * (2 ** attempt)
                        print(f"[Gemini] Rate limited (429). Retrying in {delay}s (attempt {attempt + 1}/{max_retries})...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Last attempt failed
                        raise httpx.HTTPStatusError(
                            f"Gemini API rate limit exceeded after {max_retries} attempts. Please wait before retrying.",
                            request=response.request,
                            response=response
                        )
                
                # For other errors, raise immediately
                response.raise_for_status()
                response_data = response.json()
                break  # Success - exit retry loop
                
        except httpx.TimeoutException:
            raise TimeoutError(f"Gemini API call timed out")
        except httpx.HTTPStatusError as e:
            # Re-raise if it's a 429 we couldn't handle, or other HTTP errors
            if e.response.status_code == 429 and attempt == max_retries - 1:
                raise  # Already handled above
            raise
        except Exception as e:
            # For non-HTTP errors, don't retry
            print(f"[Gemini] Error: {e}")
            raise
    
    # Extract text from response
    text = ""
    candidate = None
    finish_reason = "N/A"
    
    if isinstance(response_data, dict):
        candidates = response_data.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini API returned no candidates in response")
        
        candidate = candidates[0]
        
        # Check for safety filters or blocked content
        if "finishReason" in candidate:
            finish_reason = candidate.get("finishReason")
            if finish_reason in ["SAFETY", "RECITATION", "OTHER"]:
                safety_ratings = candidate.get("safetyRatings", [])
                reasons = [r.get("category", "UNKNOWN") for r in safety_ratings if r.get("blocked", False)]
                if reasons:
                    raise ValueError(f"Gemini API blocked content due to safety filters: {', '.join(reasons)}")
                else:
                    raise ValueError(f"Gemini API blocked content (finishReason: {finish_reason})")
        
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        if parts:
            text = parts[0].get("text", "")
        else:
            # Sometimes content is empty but not blocked - check for finishReason
            finish_reason = candidate.get("finishReason", "UNKNOWN")
            if finish_reason == "MAX_TOKENS":
                raise ValueError("Gemini API response was truncated (MAX_TOKENS) but no text was returned. Try increasing max_tokens.")
            elif finish_reason == "STOP":
                print(f"[Gemini] Warning: Response has no parts but finishReason is STOP. Content: {content}")
            else:
                print(f"[Gemini] Warning: Response has no parts. FinishReason: {finish_reason}, Content: {content}")
    else:
        # Response is not a dictionary - unexpected format
        raise ValueError(f"Gemini API returned unexpected response format: {type(response_data)}")
    
    if not text:
        # Log the full response for debugging
        print(f"[Gemini] Error: Gemini API returned empty response. Full response: {json.dumps(response_data, indent=2)}")
        # Use candidate's finishReason if available, otherwise use the one we tracked
        error_finish_reason = candidate.get('finishReason', finish_reason) if candidate else finish_reason
        raise ValueError(f"Gemini API returned empty response. Finish reason: {error_finish_reason}")
    
    # Extract usage information if available
    usage = {}
    usage_metadata = response_data.get("usageMetadata", {})
    if usage_metadata:
        usage = {
            "prompt_tokens": usage_metadata.get("promptTokenCount"),
            "completion_tokens": usage_metadata.get("candidatesTokenCount"),
            "total_tokens": usage_metadata.get("totalTokenCount"),
        }
    
    return LLMResponse(
        content=text,
        model=model_name,
        usage=usage,
    )


async def check_gemini_health() -> bool:
    """Check if Gemini API is available (with timeout)."""
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return False
        
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        params = {"key": api_key}
        request_body = {"contents": [{"parts": [{"text": "Hi"}]}]}
        
        # Use direct httpx with no timeout for health check
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(url, params=params, json=request_body)
            response.raise_for_status()
            data = response.json()
            candidates = data.get("candidates", [])
            return len(candidates) > 0 and candidates[0].get("content", {}).get("parts", [{}])[0].get("text")
    except Exception as e:
        print(f"[Gemini] Health check failed: {e}")
        return False
