"""Tests for Gmail and Slack connectors."""
import pytest
from app.connectors.gmail import get_gmail_connector
from app.connectors.slack import get_slack_connector


@pytest.mark.asyncio
async def test_gmail_connector():
    """Test Gmail connector returns normalized messages."""
    connector = get_gmail_connector()
    messages = await connector.fetch_messages("user-1", "inbox", limit=5)
    
    assert isinstance(messages, list)
    if messages:
        msg = messages[0]
        assert "id" in msg
        assert "from" in msg
        assert "to" in msg
        assert "subject" in msg
        assert "body" in msg
        assert "date" in msg


@pytest.mark.asyncio
async def test_slack_connector():
    """Test Slack connector returns normalized messages."""
    connector = get_slack_connector()
    messages = await connector.fetch_messages("user-1", "general", limit=5)
    
    assert isinstance(messages, list)
    if messages:
        msg = messages[0]
        assert "id" in msg
        assert "from" in msg
        assert "body" in msg
        assert "date" in msg

