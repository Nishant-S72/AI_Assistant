"""OpenAI LLM adapter."""
import os
from typing import Literal, Optional
from openai import AsyncOpenAI


class LLMMessage:
    """LLM message structure."""
    def __init__(self, role: Literal["system", "user", "assistant"], content: str):
        self.role = role
        self.content = content

    def to_dict(self) -> dict:
        """Convert to dictionary for API."""
        return {"role": self.role, "content": self.content}


class LLMOptions:
    """LLM request options."""
    def __init__(
        self,
        model: str,
        messages: list[LLMMessage],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ):
        self.model = model
        self.messages = messages
        self.max_tokens = max_tokens
        self.temperature = temperature


class LLMResponse:
    """LLM response structure."""
    def __init__(
        self,
        content: str,
        model: str,
        usage: Optional[dict] = None,
        function_call: Optional[dict] = None,
    ):
        self.content = content
        self.model = model
        self.usage = usage or {}
        self.function_call = function_call


async def generate_with_openai(options: LLMOptions) -> LLMResponse:
    """Generate completion using OpenAI (async)."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not configured")

    client = AsyncOpenAI(api_key=api_key)

    # Build request parameters (OpenAI doesn't accept None for max_tokens)
    request_params = {
        "model": options.model,
        "messages": [msg.to_dict() for msg in options.messages],
        "temperature": options.temperature or 0.7,
    }
    
    # Only include max_tokens if it's explicitly set (not None)
    if options.max_tokens is not None:
        request_params["max_tokens"] = options.max_tokens
    
    # Add tools if provided (for function calling)
    if hasattr(options, 'tools') and options.tools:
        request_params["tools"] = options.tools
    if hasattr(options, 'tool_choice') and options.tool_choice:
        request_params["tool_choice"] = options.tool_choice
    
    response = await client.chat.completions.create(**request_params)
    
    message = response.choices[0].message
    function_call = None
    
    # Extract function call if present
    if message.tool_calls:
        tool_call = message.tool_calls[0]
        function_call = {
            "name": tool_call.function.name,
            "arguments": tool_call.function.arguments,
        }
    elif hasattr(message, 'function_call') and message.function_call:
        # Legacy function calling format
        function_call = {
            "name": message.function_call.name,
            "arguments": message.function_call.arguments,
        }

    return LLMResponse(
        content=message.content or "",
        model=response.model,
        usage={
            "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
            "completion_tokens": response.usage.completion_tokens if response.usage else None,
            "total_tokens": response.usage.total_tokens if response.usage else None,
        },
        function_call=function_call,
    )

