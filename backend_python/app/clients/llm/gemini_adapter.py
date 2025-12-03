"""Google Gemini LLM adapter with async and timeout support."""
import os
import asyncio
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from .openai_adapter import LLMMessage, LLMOptions, LLMResponse

# Thread pool for running synchronous Gemini calls
_executor = ThreadPoolExecutor(max_workers=4)


async def generate_with_gemini(options: LLMOptions) -> LLMResponse:
    """Generate completion using Google Gemini API with async and timeout.
    
    Reference: https://ai.google.dev/gemini-api/docs/quickstart
    
    Note: The google-genai client is synchronous, so we run it in a thread pool
    to avoid blocking the event loop, with a timeout to prevent hanging.
    """
    try:
        from google import genai
    except ImportError:
        raise ImportError(
            "google-genai package not installed. Install with: pip install -q -U google-genai"
        )
    
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
    
    # Combine system prompt with user message (optimize length)
    if system_prompt and user_messages:
        # Truncate system prompt if too long (keep last 2000 chars for speed)
        if len(system_prompt) > 2000:
            system_prompt = system_prompt[-2000:]
        prompt = f"{system_prompt}\n\n{user_messages[0]}"
        if len(user_messages) > 1:
            prompt += "\n\n" + "\n\n".join(user_messages[1:])
    elif user_messages:
        prompt = "\n\n".join(user_messages)
    else:
        prompt = ""
    
    if not prompt:
        raise ValueError("No user message found in options.messages")
    
    # Truncate prompt if too long (Gemini has limits, and shorter = faster)
    max_prompt_length = int(os.getenv("GEMINI_MAX_PROMPT_LENGTH", "8000"))
    if len(prompt) > max_prompt_length:
        print(f"[Gemini] Warning: Truncating prompt from {len(prompt)} to {max_prompt_length} chars")
        prompt = prompt[-max_prompt_length:]
    
    # Get model name (default to gemini-2.5-flash - fastest model)
    model_name = options.model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # Get timeout (default 30 seconds, configurable)
    timeout_seconds = float(os.getenv("GEMINI_TIMEOUT", "30.0"))
    
    # Run synchronous Gemini call in thread pool with timeout
    def _call_gemini():
        """Synchronous Gemini API call."""
        client = genai.Client(api_key=api_key)
        
        # Generate content - use simple call first, then add config if needed
        # According to quickstart, the API is: client.models.generate_content(model="...", contents="...")
        try:
            # Try with generation config if we have max_tokens or temperature
            if options.max_tokens or options.temperature is not None:
                # Build generation config dict
                gen_config = {}
                if options.max_tokens:
                    gen_config["max_output_tokens"] = min(options.max_tokens, 1000)  # Cap at 1000 for speed
                if options.temperature is not None:
                    gen_config["temperature"] = options.temperature
                
                # Try passing as keyword argument (may vary by SDK version)
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        **gen_config  # Pass as kwargs
                    )
                except TypeError:
                    # Fallback: try without config if SDK doesn't support it
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
            else:
                # Simple call without config
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
            return response
        except Exception as e:
            print(f"[Gemini] API call error: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    try:
        # Run in thread pool with timeout
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(_executor, _call_gemini),
            timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        raise TimeoutError(f"Gemini API call timed out after {timeout_seconds} seconds")
    except Exception as e:
        print(f"[Gemini] Error: {e}")
        raise
    
    # Extract text from response
    text = ""
    if hasattr(response, 'text'):
        text = response.text
    elif hasattr(response, 'candidates') and len(response.candidates) > 0:
        # Fallback: try to extract from candidates
        candidate = response.candidates[0]
        if hasattr(candidate, 'content'):
            if hasattr(candidate.content, 'parts'):
                text = "".join([part.text for part in candidate.content.parts if hasattr(part, 'text')])
            elif hasattr(candidate.content, 'text'):
                text = candidate.content.text
    else:
        text = str(response)
    
    if not text:
        raise ValueError("Gemini API returned empty response")
    
    # Extract usage information if available
    usage = {}
    if hasattr(response, 'usage_metadata'):
        usage_metadata = response.usage_metadata
        usage = {
            "prompt_tokens": getattr(usage_metadata, 'prompt_token_count', None),
            "completion_tokens": getattr(usage_metadata, 'completion_token_count', None),
            "total_tokens": getattr(usage_metadata, 'total_token_count', None),
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
        
        from google import genai
        
        def _health_check():
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents="Hi",
            )
            return hasattr(response, 'text') and response.text
        
        # Run with 5 second timeout for health check
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(_executor, _health_check),
            timeout=5.0
        )
        return result
    except asyncio.TimeoutError:
        print("[Gemini] Health check timed out")
        return False
    except Exception as e:
        print(f"[Gemini] Health check failed: {e}")
        return False

