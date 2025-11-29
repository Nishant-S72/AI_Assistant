"""Tests for vector store seed and query."""
import pytest
import asyncio
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.clients.vectorstore.json_adapter import _json_store, query_json_store
from app.services.embeddings import get_embedding


@pytest.mark.asyncio
async def test_seed_and_query():
    """Test seeding a policy doc and querying it."""
    # Clear store first
    _json_store.vectors.clear()
    
    # Create a test chunk
    test_text = "Our refund policy states that refunds are processed within 5-7 business days for eligible purchases. Items must be returned in original condition within 30 days."
    test_embedding = await get_embedding(test_text)
    
    # Add chunk to store
    chunk_id = "test_chunk_1"
    _json_store.vectors[chunk_id] = {
        "id": chunk_id,
        "text": test_text,
        "embedding": test_embedding,
        "metadata": {
            "source": "test_policy.md",
            "title": "Refund Policy",
        }
    }
    _json_store.save()
    
    # Query for refund policy
    results = await query_json_store("What is the refund policy?", k=3)
    
    assert len(results) > 0, "Should return at least one result"
    assert results[0].id == chunk_id
    assert "refund" in results[0].text.lower()
    assert results[0].score > 0.0


@pytest.mark.asyncio
async def test_empty_store_returns_empty():
    """Test that querying empty store returns empty list."""
    _json_store.vectors.clear()
    _json_store.save()
    
    results = await query_json_store("test query", k=3)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_embedding_generation():
    """Test that embeddings are generated correctly."""
    text = "Test embedding generation"
    embedding = await get_embedding(text)
    
    assert embedding is not None
    assert len(embedding) > 0
    assert isinstance(embedding, list)
    assert all(isinstance(x, (int, float)) for x in embedding)

