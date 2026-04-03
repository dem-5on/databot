"""
Bot API client for making authenticated backend requests.
"""
import hmac
import time
import hashlib
import httpx
from typing import Optional, Dict, Any
from app.core.config import settings


def generate_signature(user_id: str, platform: str, timestamp: Optional[str] = None) -> str:
    """
    Generate HMAC-SHA256 signature for backend request authentication.
    
    Args:
        user_id: The user identifier (telegram_id or phone)
        platform: The platform ("telegram" or "whatsapp")
        timestamp: Optional Unix timestamp (added automatically if not provided)
        
    Returns:
        Hex-encoded HMAC signature
    """
    if not settings.BOT_BACKEND_SECRET:
        return "no-secret"
    
    # Include timestamp in signature for replay protection
    if timestamp is None:
        timestamp = str(int(time.time()))
    
    message = f"{user_id}:{platform}:{timestamp}"
    signature = hmac.new(
        settings.BOT_BACKEND_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature


def get_auth_headers(user_id: str, platform: str = "telegram") -> Dict[str, str]:
    """
    Get authentication headers for backend API requests.
    
    Args:
        user_id: The user identifier
        platform: The platform (default: "telegram")
        
    Returns:
        Dictionary of headers to include in requests
    """
    timestamp = str(int(time.time()))
    return {
        "X-User-ID": str(user_id),
        "X-Platform": platform,
        "X-Timestamp": timestamp,
        "X-Signature": generate_signature(str(user_id), platform, timestamp),
    }


class BotApiClient:
    """HTTP client for bot-to-backend API calls with authentication."""
    
    def __init__(self, platform: str = "telegram"):
        self.platform = platform
        self.base_url = settings.BACKEND_API_URL
        
    async def ensure_user(
        self,
        user_id: str,
        name: Optional[str] = None,
        referral_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ensure user exists in the backend.
        
        Args:
            user_id: Telegram ID or phone number
            name: User's name
            referral_code: Optional referral code
            
        Returns:
            User data from backend
            
        Raises:
            httpx.HTTPStatusError: If request fails
        """
        params = {"telegram_id": user_id}
        if name:
            params["name"] = name
        if referral_code:
            params["referral_code"] = referral_code
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/users/ensure",
                params=params,
                headers=get_auth_headers(user_id, self.platform),
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    
    async def get_balance(self, user_id: str) -> Dict[str, Any]:
        """Get user's wallet balance."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/wallet/balance/{user_id}",
                headers=get_auth_headers(user_id, self.platform),
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    
    async def get_history(self, user_id: str) -> Dict[str, Any]:
        """Get user's transaction and order history."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/users/history/{user_id}",
                headers=get_auth_headers(user_id, self.platform),
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    
    async def make_request(
        self,
        method: str,
        endpoint: str,
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make a generic authenticated request to the backend.
        
        Args:
            method: HTTP method (get, post, etc.)
            endpoint: API endpoint (e.g., "/api/v1/wallet/balance/123")
            user_id: User ID for authentication
            **kwargs: Additional arguments to pass to httpx
            
        Returns:
            Response JSON
        """
        async with httpx.AsyncClient() as client:
            headers = kwargs.pop("headers", {})
            headers.update(get_auth_headers(user_id, self.platform))
            
            response = await getattr(client, method)(
                f"{self.base_url}{endpoint}",
                headers=headers,
                timeout=kwargs.pop("timeout", 10.0),
                **kwargs
            )
            response.raise_for_status()
            return response.json()


# Singleton instances for convenience
telegram_api = BotApiClient("telegram")
whatsapp_api = BotApiClient("whatsapp")
