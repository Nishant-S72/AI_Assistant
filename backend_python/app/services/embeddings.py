"""Embedding generation service using OpenAI."""
import os
import asyncio
from typing import List


async def get_embedding(text: str, max_retries: int = 3) -> List[float]:
    """
    Generate embedding for text using OpenAI with retry logic.
    
    Args:
        text: Text to embed
        max_retries: Maximum number of retry attempts
    
    Returns:
        Embedding vector (list of floats)
    """
    if not text or not text.strip():
        print("[Embeddings] Warning: Empty text provided")
        return _generate_simple_embedding(text)
    
    # Use OpenAI for embeddings (with retry)
    if not os.getenv("OPENAI_API_KEY"):
        print("[Embeddings] ⚠️ OPENAI_API_KEY not configured, using fallback embedding")
        return _generate_simple_embedding(text)
    
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
            else:
                print(f"[Embeddings] Warning: Empty embedding from OpenAI (attempt {attempt+1})")
        except Exception as e:
            print(f"[Embeddings] OpenAI error (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            continue
    
    # Fallback: simple hash-based embedding (for demo)
    print("[Embeddings] ⚠️ OpenAI failed after retries, using fallback hash-based embedding")
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

