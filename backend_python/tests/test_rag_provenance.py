"""Tests for RAG provenance."""
import pytest
from app.rag.retriever import retrieve, format_provenance, RAGChunk


@pytest.mark.asyncio
async def test_retrieve_with_provenance():
    """Test that retriever returns chunks with metadata."""
    # Mock vector store query
    with patch("app.rag.retriever.query_json_store") as mock_query:
        from app.clients.vectorstore.json_adapter import VectorQueryResult
        
        mock_result = VectorQueryResult(
            id="chunk1",
            text="Test chunk text",
            score=0.85,
            metadata={"source": "policy.md", "filename": "policy.md", "fragment_index": 0},
        )
        mock_query.return_value = [mock_result]
        
        chunks = await retrieve("test query", top_k=1)
        
        assert len(chunks) == 1
        assert chunks[0].text == "Test chunk text"
        assert chunks[0].score == 0.85
        assert chunks[0].source == "policy.md"
        assert chunks[0].filename == "policy.md"


def test_format_provenance():
    """Test provenance formatting."""
    chunks = [
        RAGChunk("Text 1", 0.9, "source1", "file1.md", 0),
        RAGChunk("Text 2", 0.8, "source2", "file2.md", 1),
        RAGChunk("Text 3", 0.7, "source3", "file3.md", 2),
    ]
    
    provenance = format_provenance(chunks, top_n=2)
    
    assert len(provenance) == 2
    assert provenance[0]["score"] == 0.9  # Sorted by score
    assert "source" in provenance[0]
    assert "filename" in provenance[0]
    assert "snippet" in provenance[0]


@pytest.mark.asyncio
async def test_rag_chat_with_provenance():
    """Test RAG chat endpoint includes provenance."""
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    
    # Mock retriever
    with patch("app.routes.v1.rag_with_provenance.retrieve") as mock_retrieve:
        mock_chunk = RAGChunk(
            "Test text",
            0.85,
            "policy.md",
            "policy.md",
            0,
        )
        mock_retrieve.return_value = [mock_chunk]
        
        # Mock LLM
        with patch("app.routes.v1.rag_with_provenance.generate_chat_completion") as mock_llm:
            from app.clients.llm import LLMResponse
            mock_llm.return_value = LLMResponse(
                content="Test response",
                model="gpt-4o-mini",
            )
            
            response = client.post(
                "/api/v1/rag_chat",
                json={"query": "test query", "top_k": 5},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "provenance" in data
            assert len(data["provenance"]) > 0
            assert data["provenance"][0]["filename"] == "policy.md"


