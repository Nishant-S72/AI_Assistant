"""Gmail connector with OAuth support."""
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
import os
import httpx
from app.connectors.token_store import get_token_store


# OAuth configuration (from environment)
GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID", "")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET", "")
GMAIL_REDIRECT_URI = os.getenv("GMAIL_REDIRECT_URI", "http://localhost:3001/api/connectors/gmail/callback")
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


def build_auth_url(state: Optional[str] = None) -> str:
    """
    Build Gmail OAuth authorization URL.
    
    Args:
        state: Optional state parameter for CSRF protection
    
    Returns:
        Authorization URL
    """
    if not GMAIL_CLIENT_ID:
        raise ValueError("GMAIL_CLIENT_ID not configured")
    
    params = {
        "client_id": GMAIL_CLIENT_ID,
        "redirect_uri": GMAIL_REDIRECT_URI,
        "response_type": "code",
        "scope": GMAIL_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    
    if state:
        params["state"] = state
    
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


async def exchange_code(code: str) -> Dict[str, Any]:
    """
    Exchange authorization code for access token.
    
    Args:
        code: Authorization code from OAuth callback
    
    Returns:
        Token dictionary with access_token, refresh_token, etc.
    """
    if not GMAIL_CLIENT_SECRET:
        raise ValueError("GMAIL_CLIENT_SECRET not configured")
    
    # TODO: Implement actual token exchange
    # This is a stub - replace with actual Google OAuth token exchange
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GMAIL_CLIENT_ID,
                "client_secret": GMAIL_CLIENT_SECRET,
                "redirect_uri": GMAIL_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        return response.json()


async def fetch_messages(user_id: str, folder: str = "inbox") -> List[Dict[str, Any]]:
    """
    Fetch messages from Gmail.
    
    Args:
        user_id: User ID
        folder: Folder name (inbox, sent, etc.)
    
    Returns:
        List of normalized message dicts with: id, from, to, subject, body, date
    """
    token_store = get_token_store()
    token = await token_store.get_token(user_id, "gmail")
    
    if not token:
        raise ValueError("Gmail token not found. User must authorize first.")
    
    access_token = token.get("access_token")
    if not access_token:
        raise ValueError("Invalid token: missing access_token")
    
    # TODO: Implement actual Gmail API call
    # This is a stub - replace with actual Gmail API requests
    async with httpx.AsyncClient() as client:
        # List messages
        list_response = await client.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"q": f"in:{folder}", "maxResults": 50},
        )
        list_response.raise_for_status()
        messages_list = list_response.json()
        
        # Fetch full message details
        normalized_messages = []
        for msg_summary in messages_list.get("messages", [])[:10]:  # Limit to 10 for stub
            msg_id = msg_summary["id"]
            msg_response = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            msg_response.raise_for_status()
            msg_data = msg_response.json()
            
            # Normalize to common format
            headers = {h["name"].lower(): h["value"] for h in msg_data.get("payload", {}).get("headers", [])}
            
            normalized_messages.append({
                "id": msg_id,
                "from": headers.get("from", ""),
                "to": headers.get("to", ""),
                "subject": headers.get("subject", ""),
                "body": _extract_body(msg_data.get("payload", {})),
                "date": headers.get("date", ""),
            })
        
        return normalized_messages


def _extract_body(payload: Dict[str, Any]) -> str:
    """Extract body text from Gmail message payload."""
    # TODO: Handle multipart messages, HTML, etc.
    if "body" in payload and "data" in payload["body"]:
        import base64
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    return ""
