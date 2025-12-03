"""Tests for RBAC."""
import pytest
from app.middleware.rbac import require_admin_role, get_current_user
from fastapi import HTTPException
from unittest.mock import patch


@pytest.mark.asyncio
async def test_require_admin_role():
    """Test admin role requirement."""
    # Test with admin user
    admin_user = {"id": "admin-1", "role": "admin"}
    result = await require_admin_role(admin_user)
    assert result == admin_user
    
    # Test with non-admin user
    user = {"id": "user-1", "role": "user"}
    with pytest.raises(HTTPException) as exc_info:
        await require_admin_role(user)
    assert exc_info.value.status_code == 403

