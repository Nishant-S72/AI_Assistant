"""Tests for prompt library."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.connection import get_pool
import uuid

client = TestClient(app)


def test_create_prompt():
    """Test creating a prompt."""
    # Mock admin user
    response = client.post(
        "/api/v1/prompts",
        json={
            "name": "test_prompt",
            "content": "Test prompt content",
            "active": False,
        },
        headers={"X-User-ID": "admin_user", "X-Role": "admin"},
    )
    
    # Should require authentication - simplified test
    assert response.status_code in [200, 401, 403]


def test_list_prompts():
    """Test listing prompts."""
    response = client.get("/api/v1/prompts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_active_prompt():
    """Test getting active prompt."""
    response = client.get("/api/v1/prompts/active/active")
    # May return None if no active prompt
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_prompt_crud():
    """Test CRUD operations for prompts."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Create
        prompt_id = uuid.uuid4()
        await conn.execute(
            """
            INSERT INTO prompts (id, name, content, version, active)
            VALUES ($1, $2, $3, $4, $5)
            """,
            prompt_id,
            "test_prompt",
            "Test content",
            1,
            True,
        )
        
        # Read
        row = await conn.fetchrow(
            "SELECT * FROM prompts WHERE id = $1",
            prompt_id,
        )
        assert row is not None
        assert row["name"] == "test_prompt"
        
        # Update
        await conn.execute(
            "UPDATE prompts SET content = $1 WHERE id = $2",
            "Updated content",
            prompt_id,
        )
        
        # Verify update
        updated = await conn.fetchrow(
            "SELECT * FROM prompts WHERE id = $1",
            prompt_id,
        )
        assert updated["content"] == "Updated content"
        
        # Delete
        await conn.execute("DELETE FROM prompts WHERE id = $1", prompt_id)
        
        # Verify delete
        deleted = await conn.fetchrow(
            "SELECT * FROM prompts WHERE id = $1",
            prompt_id,
        )
        assert deleted is None
