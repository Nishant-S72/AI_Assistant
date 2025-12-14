"""Token storage interface for OAuth tokens."""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import os
import json
from pathlib import Path


class TokenStore(ABC):
    """Abstract token store interface."""
    
    @abstractmethod
    async def get_token(self, user_id: str, service: str) -> Optional[Dict[str, Any]]:
        """Get stored token for user and service."""
        pass
    
    @abstractmethod
    async def save_token(self, user_id: str, service: str, token: Dict[str, Any]):
        """Save token for user and service."""
        pass
    
    @abstractmethod
    async def delete_token(self, user_id: str, service: str):
        """Delete token for user and service."""
        pass


class FileTokenStore(TokenStore):
    """Simple file-based token store (for development)."""
    
    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir or os.getenv("TOKEN_STORE_DIR", "backend_python/storage/tokens"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, user_id: str, service: str) -> Path:
        """Get file path for token."""
        return self.storage_dir / f"{user_id}_{service}.json"
    
    async def get_token(self, user_id: str, service: str) -> Optional[Dict[str, Any]]:
        """Get stored token."""
        file_path = self._get_file_path(user_id, service)
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[TokenStore] Error reading token: {e}")
            return None
    
    async def save_token(self, user_id: str, service: str, token: Dict[str, Any]):
        """Save token."""
        file_path = self._get_file_path(user_id, service)
        try:
            with open(file_path, "w") as f:
                json.dump(token, f, indent=2)
        except Exception as e:
            print(f"[TokenStore] Error saving token: {e}")
            raise
    
    async def delete_token(self, user_id: str, service: str):
        """Delete token."""
        file_path = self._get_file_path(user_id, service)
        if file_path.exists():
            file_path.unlink()


# Global token store instance
_token_store: Optional[TokenStore] = None


def get_token_store() -> TokenStore:
    """Get global token store."""
    global _token_store
    if _token_store is None:
        _token_store = FileTokenStore()
    return _token_store


