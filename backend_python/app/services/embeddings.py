"""Embedding generation service."""
import os
import httpx
from typing import List


async def get_embedding(text: str) -> List[float]:
    """
    Generate embedding for text.
    Tries Ollama first, then OpenAI, then fallback to simple hash-based embedding.
    """
    # Try Ollama if configured
    if os.getenv("USE_OLLAMA") != "false":
        try:
            base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{base_url}/api/embeddings",
                    json={
                        "model": os.getenv("LLM_MODEL", "tinyllama"),
                        "prompt": text,
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("embedding"):
                        return data["embedding"]
        except Exception as e:
            print(f"[Embeddings] Ollama failed: {e}")
    
    # Try OpenAI if configured
    if os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[Embeddings] OpenAI failed: {e}")
    
    # Fallback: simple hash-based embedding (for demo)
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

