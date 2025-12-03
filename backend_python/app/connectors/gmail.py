"""Gmail connector (OAuth + message fetch)."""
from typing import List, Dict, Any, Optional
import os


class GmailConnector:
    """Gmail connector with OAuth flow."""
    
    def __init__(self):
        # TODO: Load OAuth credentials from environment
        self.client_id = os.getenv("GMAIL_CLIENT_ID")
        self.client_secret = os.getenv("GMAIL_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GMAIL_REDIRECT_URI", "http://localhost:3000/oauth/gmail/callback")
    
    async def get_oauth_url(self, user_id: str) -> str:
        """
        Generate OAuth authorization URL.
        
        TODO: Implement actual OAuth flow with Google
        """
        # Stub implementation
        return f"https://accounts.google.com/o/oauth2/auth?client_id={self.client_id}&redirect_uri={self.redirect_uri}&scope=read&response_type=code&state={user_id}"
    
    async def store_token(self, user_id: str, token: str):
        """Store OAuth token for user."""
        # TODO: Store token in database
        pass
    
    async def fetch_messages(
        self,
        user_id: str,
        folder: str = "inbox",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Fetch messages from Gmail.
        
        Returns normalized message schema:
        - id: Message ID
        - from: Sender email
        - to: Recipient email
        - subject: Email subject
        - body: Email body
        - date: Message date
        """
        # TODO: Implement actual Gmail API call
        # For now, return mock data
        return [
            {
                "id": f"gmail-{i}",
                "from": f"sender{i}@example.com",
                "to": f"user{user_id}@example.com",
                "subject": f"Sample email {i}",
                "body": f"This is a sample email body {i}",
                "date": "2024-01-01T00:00:00Z",
            }
            for i in range(min(limit, 5))
        ]


# Global connector instance
_gmail_connector = GmailConnector()


def get_gmail_connector() -> GmailConnector:
    """Get global Gmail connector."""
    return _gmail_connector

