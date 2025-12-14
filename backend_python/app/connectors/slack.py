"""Slack connector with OAuth support."""
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
import os
import httpx
from app.connectors.token_store import get_token_store


# OAuth configuration (from environment)
SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID", "")
SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET", "")
SLACK_REDIRECT_URI = os.getenv("SLACK_REDIRECT_URI", "http://localhost:3001/api/connectors/slack/callback")
SLACK_SCOPE = "channels:read,channels:history,im:read,im:history"


def build_auth_url(state: Optional[str] = None) -> str:
    """
    Build Slack OAuth authorization URL.
    
    Args:
        state: Optional state parameter for CSRF protection
    
    Returns:
        Authorization URL
    """
    if not SLACK_CLIENT_ID:
        raise ValueError("SLACK_CLIENT_ID not configured")
    
    params = {
        "client_id": SLACK_CLIENT_ID,
        "redirect_uri": SLACK_REDIRECT_URI,
        "scope": SLACK_SCOPE,
        "state": state or "",
    }
    
    return f"https://slack.com/oauth/v2/authorize?{urlencode(params)}"


async def exchange_code(code: str) -> Dict[str, Any]:
    """
    Exchange authorization code for access token.
    
    Args:
        code: Authorization code from OAuth callback
    
    Returns:
        Token dictionary with access_token, etc.
    """
    if not SLACK_CLIENT_SECRET:
        raise ValueError("SLACK_CLIENT_SECRET not configured")
    
    # TODO: Implement actual token exchange
    # This is a stub - replace with actual Slack OAuth token exchange
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "code": code,
                "client_id": SLACK_CLIENT_ID,
                "client_secret": SLACK_CLIENT_SECRET,
                "redirect_uri": SLACK_REDIRECT_URI,
            },
        )
        response.raise_for_status()
        data = response.json()
        
        if not data.get("ok"):
            raise ValueError(f"Slack OAuth error: {data.get('error')}")
        
        return {
            "access_token": data.get("access_token"),
            "team": data.get("team"),
            "authed_user": data.get("authed_user"),
        }


async def fetch_messages(user_id: str, channel: str = "general") -> List[Dict[str, Any]]:
    """
    Fetch messages from Slack channel.
    
    Args:
        user_id: User ID
        channel: Channel name or ID
    
    Returns:
        List of normalized message dicts with: id, from, to, subject, body, date
    """
    token_store = get_token_store()
    token = await token_store.get_token(user_id, "slack")
    
    if not token:
        raise ValueError("Slack token not found. User must authorize first.")
    
    access_token = token.get("access_token")
    if not access_token:
        raise ValueError("Invalid token: missing access_token")
    
    # TODO: Implement actual Slack API call
    # This is a stub - replace with actual Slack API requests
    async with httpx.AsyncClient() as client:
        # Get channel history
        response = await client.get(
            "https://slack.com/api/conversations.history",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"channel": channel, "limit": 50},
        )
        response.raise_for_status()
        data = response.json()
        
        if not data.get("ok"):
            raise ValueError(f"Slack API error: {data.get('error')}")
        
        # Normalize to common format
        normalized_messages = []
        for msg in data.get("messages", [])[:10]:  # Limit to 10 for stub
            normalized_messages.append({
                "id": msg.get("ts", ""),
                "from": msg.get("user", ""),
                "to": channel,
                "subject": "",  # Slack messages don't have subjects
                "body": msg.get("text", ""),
                "date": msg.get("ts", ""),
            })
        
        return normalized_messages
