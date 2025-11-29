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
    ):
        self.content = content
        self.model = model
        self.usage = usage or {}


async def generate_with_openai(options: LLMOptions) -> LLMResponse:
    """Generate completion using OpenAI (async)."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not configured")

    client = AsyncOpenAI(api_key=api_key)

    response = await client.chat.completions.create(
        model=options.model,
        messages=[msg.to_dict() for msg in options.messages],
        max_tokens=options.max_tokens,
        temperature=options.temperature or 0.7,
    )

    return LLMResponse(
        content=response.choices[0].message.content or "",
        model=response.model,
        usage={
            "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
            "completion_tokens": response.usage.completion_tokens if response.usage else None,
            "total_tokens": response.usage.total_tokens if response.usage else None,
        },
    )

