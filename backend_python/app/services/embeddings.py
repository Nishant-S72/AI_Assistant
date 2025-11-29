"""Embedding generation service with retry logic."""
import os
import httpx
import asyncio
from typing import List


async def get_embedding(text: str, max_retries: int = 3) -> List[float]:
    """
    Generate embedding for text with retry logic.
    Tries Ollama first, then OpenAI, then fallback to simple hash-based embedding.
    
    Args:
        text: Text to embed
        max_retries: Maximum number of retry attempts
    
    Returns:
        Embedding vector (list of floats)
    """
    if not text or not text.strip():
        print("[Embeddings] Warning: Empty text provided")
        return _generate_simple_embedding(text)
    
    # Try Ollama if configured (with retry)
    if os.getenv("USE_OLLAMA") != "false":
        base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        
        for attempt in range(max_retries):
            try:
                timeout = 10.0 * (attempt + 1)  # Exponential backoff timeout
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        f"{base_url}/api/embeddings",
                        json={
                            "model": os.getenv("LLM_MODEL", "tinyllama"),
                            "prompt": text,
                        }
                    )
                    if response.status_code == 200:
                        data = response.json()
                        embedding = data.get("embedding")
                        if embedding and len(embedding) > 0:
                            print(f"[Embeddings] ✅ Generated embedding (length: {len(embedding)})")
                            return embedding
                        else:
                            print(f"[Embeddings] Warning: Empty embedding from Ollama (attempt {attempt+1})")
                    else:
                        print(f"[Embeddings] Ollama returned status {response.status_code} (attempt {attempt+1})")
            except httpx.TimeoutException:
                print(f"[Embeddings] Ollama timeout (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                continue
            except Exception as e:
                print(f"[Embeddings] Ollama error (attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                continue
    
    # Try OpenAI if configured (with retry)
    if os.getenv("OPENAI_API_KEY"):
        for attempt in range(max_retries):
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                response = await client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text
                )
                embedding = response.data[0].embedding
                if embedding and len(embedding) > 0:
                    print(f"[Embeddings] ✅ Generated OpenAI embedding (length: {len(embedding)})")
                    return embedding
            except Exception as e:
                print(f"[Embeddings] OpenAI error (attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                continue
    
    # Fallback: simple hash-based embedding (for demo)
    print("[Embeddings] ⚠️ Using fallback hash-based embedding")
    return _generate_simple_embedding(text)


def _generate_simple_embedding(text: str) -> List[float]:
    """Generate simple hash-based embedding (not real embedding, but works for demo)."""
    embedding = [0.0] * 384
    words = text.lower().split()
    
    for i, word in enumerate(words):
        hash_val = hash(word) % len(embedding)
        embedding[hash_val] += 1.0 / (i + 1)
    
    # Normalize
    magnitude = sum(x * x for x in embedding) ** 0.5
    if magnitude > 0:
        return [x / magnitude for x in embedding]
    
    return embedding

