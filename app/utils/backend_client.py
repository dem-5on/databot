import httpx
from app.core.config import settings

class BackendAPIClient:
    """Shared HTTP client for backend API requests with connection pooling."""
    
    _client: httpx.AsyncClient = None
    
    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        """Get the shared HTTP client instance."""
        if cls._client is None:
            cls._client = httpx.AsyncClient(
                timeout=30.0,
                limits=httpx.Limits(
                    max_keepalive_connections=settings.MAX_KEEPALIVE_CONNECTIONS,
                    max_connections=settings.MAX_CONNECTIONS
                )
            )
        return cls._client
    
    @classmethod
    async def close_client(cls):
        """Close the shared HTTP client."""
        if cls._client is not None:
            await cls._client.aclose()
            cls._client = None
