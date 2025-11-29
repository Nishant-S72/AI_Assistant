"""Ollama LLM adapter."""
import os
import json
from typing import Optional
import httpx
from .openai_adapter import LLMMessage, LLMOptions, LLMResponse


async def generate_with_ollama(options: LLMOptions) -> LLMResponse:
    """Generate completion using Ollama."""
    base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
    model = options.model or os.getenv("LLM_MODEL", "phi3")

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": [msg.to_dict() for msg in options.messages],
                "stream": False,
                "options": {
                    "temperature": options.temperature or 0.7,
                    "num_predict": options.max_tokens or 500,
                    "num_ctx": 2048,
                    "top_k": 20,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1,
                    "num_thread": 2,
                    "numa": False,
                },
            },
        )

        if response.status_code != 200:
            raise ValueError(f"Ollama API error: {response.status_code} - {response.text}")

        # Ollama may return streaming JSON (multiple lines) even with stream:false
        text = response.text
        try:
            # Try parsing as single JSON first
            data = response.json()
        except json.JSONDecodeError:
            # If it's streaming format (multiple JSON lines), parse all chunks
            lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
            if not lines:
                raise ValueError("Ollama returned empty response")

            # Accumulate content from all chunks
            full_content = ""
            final_data = None
            model_name = model
            prompt_tokens = 0
            completion_tokens = 0

            for line in lines:
                try:
                    chunk = json.loads(line)
                    if chunk.get("message", {}).get("content"):
                        full_content += chunk["message"]["content"]
                    if chunk.get("model"):
                        model_name = chunk["model"]
                    if chunk.get("prompt_eval_count"):
                        prompt_tokens = chunk["prompt_eval_count"]
                    if chunk.get("eval_count"):
                        completion_tokens = chunk["eval_count"]
                    if chunk.get("done"):
                        final_data = chunk
                except json.JSONDecodeError:
                    continue

            # Use final chunk if available
            if final_data:
                data = {
                    **final_data,
                    "message": {"content": full_content or final_data.get("message", {}).get("content", "")},
                    "model": model_name,
                    "prompt_eval_count": prompt_tokens,
                    "eval_count": completion_tokens,
                }
            elif full_content:
                data = {
                    "message": {"content": full_content},
                    "model": model_name,
                    "prompt_eval_count": prompt_tokens,
                    "eval_count": completion_tokens,
                }
            else:
                # Last resort: try to parse the last line
                data = json.loads(lines[-1])

    return LLMResponse(
        content=data.get("message", {}).get("content", ""),
        model=data.get("model", model),
        usage={
            "prompt_tokens": data.get("prompt_eval_count"),
            "completion_tokens": data.get("eval_count"),
            "total_tokens": (data.get("prompt_eval_count") or 0) + (data.get("eval_count") or 0),
        },
    )


async def check_ollama_health() -> bool:
    """Check if Ollama is available."""
    try:
        base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{base_url}/api/tags")
            return response.status_code == 200
    except Exception:
        return False

