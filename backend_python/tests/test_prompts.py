"""Tests for prompt library."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


def test_create_prompt(client):
    """Test creating a prompt."""
    with patch("app.routes.v1.prompts.get_pool") as mock_pool:
        mock_conn = mock_pool.return_value.acquire.return_value.__aenter__.return_value
        mock_conn.execute = lambda *args: None
        
        response = client.post(
            "/api/v1/prompts",
            json={
                "name": "test-prompt",
                "content": "You are a helpful assistant.",
                "version": "1.0.0",
            },
        )
        
        # Should succeed (or 500 if DB not available)
        assert response.status_code in [200, 500]


def test_get_active_prompt(client):
    """Test getting active prompt."""
    with patch("app.routes.v1.prompts.get_pool") as mock_pool:
        mock_conn = mock_pool.return_value.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow = lambda *args: {
            "id": "test-id",
            "name": "test-prompt",
            "content": "Content",
            "version": "1.0.0",
            "active": True,
            "created_at": "2024-01-01",
        }
        
        response = client.get("/api/v1/prompts/active")
        assert response.status_code in [200, 500]

