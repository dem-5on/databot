import hmac
import time
import hashlib
import httpx
from app.core.config import settings


class BackendAPIClient:
    """Shared HTTP client for backend API requests with connection pooling."""
    
    _client: httpx.AsyncClient = None
    
    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        """Get the shared HTTP client instance with proper timeout configuration."""
        if cls._client is None or cls._client.is_closed:
            # Configure timeout with separate values for different phases
            timeout = httpx.Timeout(
                connect=10.0,   # Time to establish connection
                read=30.0,      # Time to read response
                write=10.0,     # Time to send request
                pool=10.0,      # Time to acquire connection from pool
            )
            
            cls._client = httpx.AsyncClient(
                timeout=timeout,
                limits=httpx.Limits(
                    max_keepalive_connections=settings.MAX_KEEPALIVE_CONNECTIONS,
                    max_connections=settings.MAX_CONNECTIONS,
                    keepalive_expiry=30.0,  # Close idle connections after 30s
                ),
                # Don't reuse connections that might be stale
                http2=False,
            )
        return cls._client
    
    @classmethod
    async def close_client(cls):
        """Close the shared HTTP client."""
        if cls._client is not None:
            await cls._client.aclose()
            cls._client = None
    
    @classmethod
    async def reset_client(cls):
        """Reset the client (close and recreate). Use after connection errors."""
        await cls.close_client()
        return cls.get_client()
    
    @classmethod
    def get_auth_headers(cls, user_id: str, platform: str) -> dict:
        """
        Generate authentication headers for backend API requests.
        
        Args:
            user_id: User identifier (telegram_id or phone)
            platform: Platform name ("telegram" or "whatsapp")
            
        Returns:
            Dict with X-User-ID, X-Platform, X-Signature, X-Timestamp headers
        """
        timestamp = str(int(time.time()))
        message = f"{user_id}:{platform}:{timestamp}"
        
        # Generate HMAC signature
        signature = hmac.new(
            settings.BOT_BACKEND_SECRET.encode() if settings.BOT_BACKEND_SECRET else b"",
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return {
            "X-User-ID": str(user_id),
            "X-Platform": platform,
            "X-Signature": signature,
            "X-Timestamp": timestamp
        }
