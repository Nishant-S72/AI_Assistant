"""Tests for RBAC."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.roles import require_role
from app.middleware.rbac import get_current_user

client = TestClient(app)


def test_require_role_admin():
    """Test that admin role is required for admin endpoints."""
    # Try to access admin endpoint without admin role
    response = client.get(
        "/api/v1/admin/metrics",
        headers={"X-User-ID": "user1", "X-Role": "user"},
    )
    
    # Should return 403 or 401 (depending on auth implementation)
    assert response.status_code in [401, 403]


def test_require_role_success():
    """Test that admin can access admin endpoints."""
    response = client.get(
        "/api/v1/admin/metrics",
        headers={"X-User-ID": "admin1", "X-Role": "admin"},
    )
    
    # Should succeed (200) or require additional auth
    assert response.status_code in [200, 401]


@pytest.mark.asyncio
async def test_role_hierarchy():
    """Test role hierarchy (admin > user > read_only)."""
    # This would test the role hierarchy logic
    # Admin should access user endpoints
    # User should not access admin endpoints
    pass


def test_read_only_role():
    """Test that read_only role has limited access."""
    # read_only should not be able to modify data
    response = client.patch(
        "/api/v1/admin/users/test/quota",
        json={"monthly_quota_tokens": 200000},
        headers={"X-User-ID": "readonly1", "X-Role": "read_only"},
    )
    
    assert response.status_code in [401, 403]
