"""LLM fallback adapter - tries Gemini first, then Ollama, then OpenAI."""
import os
import uuid
import time
from typing import Optional
from .openai_adapter import LLMMessage, LLMOptions, LLMResponse, generate_with_openai
from .ollama_adapter import generate_with_ollama, check_ollama_health
from .gemini_adapter import generate_with_gemini, check_gemini_health


class LLMRequestOptions(LLMOptions):
    """Extended LLM options with local/fallback settings."""
    def __init__(
        self,
        model: str,
        messages: list[LLMMessage],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        use_local: Optional[bool] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(model, messages, max_tokens, temperature)
        self.use_local = use_local
        self.correlation_id = correlation_id


async def generate_chat_completion(
    options: LLMRequestOptions,
) -> LLMResponse:
    """Generate chat completion with automatic fallback: Gemini -> Ollama -> OpenAI."""
    correlation_id = options.correlation_id or str(uuid.uuid4())
    errors = []
    
    # Response wrapper class
    class Response:
        def __init__(self, content, model, usage, correlation_id, adapter):
            self.content = content
            self.model = model
            self.usage = usage
            self.correlation_id = correlation_id
            self.adapter = adapter

    # Try Gemini first (primary LLM)
    if os.getenv("GEMINI_API_KEY"):
        try:
            is_healthy = await check_gemini_health()
            if is_healthy:
                start_time = time.time()
                result = await generate_with_gemini(options)
                latency = int((time.time() - start_time) * 1000)
                print(f"[LLM] Gemini success ({latency}ms) - correlationId: {correlation_id}")
                return Response(result.content, result.model, result.usage, correlation_id, "gemini")
            else:
                errors.append({"adapter": "gemini", "error": "Health check failed"})
        except Exception as error:
            error_msg = str(error)
            errors.append({"adapter": "gemini", "error": error_msg})
            print(f"[LLM] Gemini failed: {error_msg}")

    # Fallback to Ollama if configured
    use_ollama = options.use_local is not False and (
        options.use_local is True or os.getenv("USE_OLLAMA") != "false"
    )
    
    if use_ollama:
        try:
            is_healthy = await check_ollama_health()
            if is_healthy:
                start_time = time.time()
                result = await generate_with_ollama(options)
                latency = int((time.time() - start_time) * 1000)
                print(f"[LLM] Ollama success ({latency}ms) - correlationId: {correlation_id}")
                return Response(result.content, result.model, result.usage, correlation_id, "ollama")
            else:
                errors.append({"adapter": "ollama", "error": "Health check failed"})
        except Exception as error:
            error_msg = str(error)
            errors.append({"adapter": "ollama", "error": error_msg})
            print(f"[LLM] Ollama failed: {error_msg}")

    # Fallback to OpenAI
    if os.getenv("OPENAI_API_KEY"):
        try:
            start_time = time.time()
            result = await generate_with_openai(options)
            latency = int((time.time() - start_time) * 1000)
            print(f"[LLM] OpenAI success ({latency}ms) - correlationId: {correlation_id}")
            return Response(result.content, result.model, result.usage, correlation_id, "openai")
        except Exception as error:
            error_msg = str(error)
            errors.append({"adapter": "openai", "error": error_msg})
            print(f"[LLM] OpenAI failed: {error_msg}")

    # All adapters failed
    error_message = "All LLM adapters failed:\n" + "\n".join(
        [f"  - {e['adapter']}: {e['error']}" for e in errors]
    )
    raise RuntimeError(error_message)

