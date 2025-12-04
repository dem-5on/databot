import httpx
from app.core.config import settings


class BackendAPIClient:
    """Shared HTTP client for backend API requests."""
    
    _client: httpx.AsyncClient = None
    
    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        """Get or create the shared HTTP client."""
        if cls._client is None:
            cls._client = httpx.AsyncClient(
                timeout=30.0,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
            )
        return cls._client
    
    @classmethod
    async def close_client(cls):
        """Close the shared HTTP client."""
        if cls._client is not None:
            await cls._client.aclose()
            cls._client = None
