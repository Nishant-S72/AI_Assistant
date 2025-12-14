"""Tests for connector skeletons."""
import pytest
from unittest.mock import AsyncMock, patch
from app.connectors.gmail import build_auth_url, exchange_code, fetch_messages
from app.connectors.slack import build_auth_url as slack_build_auth_url, exchange_code as slack_exchange_code, fetch_messages as slack_fetch_messages
from app.connectors.token_store import FileTokenStore, get_token_store


def test_gmail_build_auth_url():
    """Test Gmail OAuth URL building."""
    with patch.dict("os.environ", {"GMAIL_CLIENT_ID": "test_client_id"}):
        url = build_auth_url(state="test_state")
        assert "accounts.google.com" in url
        assert "test_client_id" in url
        assert "test_state" in url


@pytest.mark.asyncio
async def test_gmail_exchange_code():
    """Test Gmail code exchange (mocked)."""
    with patch("app.connectors.gmail.httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "access_token": "test_token",
            "refresh_token": "test_refresh",
        }
        mock_response.raise_for_status = AsyncMock()
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        token = await exchange_code("test_code")
        assert "access_token" in token


@pytest.mark.asyncio
async def test_gmail_fetch_messages():
    """Test Gmail message fetching (mocked)."""
    token_store = FileTokenStore()
    await token_store.save_token("test_user", "gmail", {
        "access_token": "test_token",
    })
    
    with patch("app.connectors.gmail.get_token_store", return_value=token_store):
        with patch("app.connectors.gmail.httpx.AsyncClient") as mock_client:
            # Mock list response
            list_mock = AsyncMock()
            list_mock.json.return_value = {
                "messages": [{"id": "msg1"}, {"id": "msg2"}],
            }
            list_mock.raise_for_status = AsyncMock()
            
            # Mock message detail response
            detail_mock = AsyncMock()
            detail_mock.json.return_value = {
                "id": "msg1",
                "payload": {
                    "headers": [
                        {"name": "From", "value": "test@example.com"},
                        {"name": "Subject", "value": "Test"},
                    ],
                    "body": {"data": "dGVzdA=="},  # base64 "test"
                },
            }
            detail_mock.raise_for_status = AsyncMock()
            
            mock_post = AsyncMock(side_effect=[list_mock, detail_mock, detail_mock])
            mock_client.return_value.__aenter__.return_value.get = mock_post
            
            messages = await fetch_messages("test_user", "inbox")
            assert len(messages) > 0
            assert "id" in messages[0]
            assert "from" in messages[0]


def test_slack_build_auth_url():
    """Test Slack OAuth URL building."""
    with patch.dict("os.environ", {"SLACK_CLIENT_ID": "test_client_id"}):
        url = slack_build_auth_url(state="test_state")
        assert "slack.com" in url
        assert "test_client_id" in url


@pytest.mark.asyncio
async def test_slack_exchange_code():
    """Test Slack code exchange (mocked)."""
    with patch("app.connectors.slack.httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "ok": True,
            "access_token": "test_token",
        }
        mock_response.raise_for_status = AsyncMock()
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        token = await slack_exchange_code("test_code")
        assert "access_token" in token


@pytest.mark.asyncio
async def test_token_store():
    """Test token store operations."""
    store = FileTokenStore()
    
    # Save
    await store.save_token("user1", "gmail", {"access_token": "token1"})
    
    # Get
    token = await store.get_token("user1", "gmail")
    assert token is not None
    assert token["access_token"] == "token1"
    
    # Delete
    await store.delete_token("user1", "gmail")
    
    # Verify deleted
    token = await store.get_token("user1", "gmail")
    assert token is None
