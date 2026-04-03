import asyncio
import logging
from functools import wraps
from typing import Any, Callable
from app.core.config import settings
from supabase import create_client, Client

logger = logging.getLogger(__name__)


class AsyncSupabaseClient:
    """
    Async wrapper for Supabase client.
    
    This wraps synchronous Supabase operations to run in a thread pool,
    making them truly async and non-blocking for FastAPI.
    """
    
    def __init__(self, client: Client):
        self._client = client
    
    def _make_async(self, func: Callable) -> Callable:
        """
        Decorator to make synchronous functions async by running them in a thread pool.
        """
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
        return async_wrapper
    
    def table(self, table_name: str) -> "AsyncTableWrapper":
        """Get an async-wrapped table."""
        return AsyncTableWrapper(self._client.table(table_name))
    
    async def rpc(self, function_name: str, params: dict = None) -> Any:
        """
        Call a PostgreSQL function (RPC) asynchronously.
        
        Args:
            function_name: Name of the PostgreSQL function
            params: Parameters to pass to the function
            
        Returns:
            The function result
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            lambda: self._client.rpc(function_name, params or {}).execute()
        )
    
    @property
    def auth(self):
        """Access auth methods (if needed)."""
        return self._client.auth
    
    @property
    def storage(self):
        """Access storage methods (if needed)."""
        return self._client.storage


class AsyncTableWrapper:
    """Async wrapper for Supabase table operations."""
    
    def __init__(self, table):
        self._table = table
        self._query = table
    
    def select(self, *args, **kwargs) -> "AsyncTableWrapper":
        """Select columns."""
        self._query = self._query.select(*args, **kwargs)
        return self
    
    def insert(self, data: dict | list, **kwargs) -> "AsyncTableWrapper":
        """Insert data."""
        self._query = self._query.insert(data, **kwargs)
        return self
    
    def update(self, data: dict, **kwargs) -> "AsyncTableWrapper":
        """Update data."""
        self._query = self._query.update(data, **kwargs)
        return self
    
    def upsert(self, data: dict | list, **kwargs) -> "AsyncTableWrapper":
        """Upsert data."""
        self._query = self._query.upsert(data, **kwargs)
        return self
    
    def delete(self, **kwargs) -> "AsyncTableWrapper":
        """Delete data."""
        self._query = self._query.delete(**kwargs)
        return self
    
    def eq(self, column: str, value: Any) -> "AsyncTableWrapper":
        """Filter: column equals value."""
        self._query = self._query.eq(column, value)
        return self
    
    def neq(self, column: str, value: Any) -> "AsyncTableWrapper":
        """Filter: column not equals value."""
        self._query = self._query.neq(column, value)
        return self
    
    def gt(self, column: str, value: Any) -> "AsyncTableWrapper":
        """Filter: column greater than value."""
        self._query = self._query.gt(column, value)
        return self
    
    def gte(self, column: str, value: Any) -> "AsyncTableWrapper":
        """Filter: column greater than or equal to value."""
        self._query = self._query.gte(column, value)
        return self
    
    def lt(self, column: str, value: Any) -> "AsyncTableWrapper":
        """Filter: column less than value."""
        self._query = self._query.lt(column, value)
        return self
    
    def lte(self, column: str, value: Any) -> "AsyncTableWrapper":
        """Filter: column less than or equal to value."""
        self._query = self._query.lte(column, value)
        return self
    
    def like(self, column: str, pattern: str) -> "AsyncTableWrapper":
        """Filter: column matches pattern (case-sensitive)."""
        self._query = self._query.like(column, pattern)
        return self
    
    def ilike(self, column: str, pattern: str) -> "AsyncTableWrapper":
        """Filter: column matches pattern (case-insensitive)."""
        self._query = self._query.ilike(column, pattern)
        return self
    
    def is_(self, column: str, value: Any) -> "AsyncTableWrapper":
        """Filter: column is value (for NULL checks)."""
        self._query = self._query.is_(column, value)
        return self
    
    def in_(self, column: str, values: list) -> "AsyncTableWrapper":
        """Filter: column value in list."""
        self._query = self._query.in_(column, values)
        return self
    
    def contains(self, column: str, value: Any) -> "AsyncTableWrapper":
        """Filter: column contains value (for arrays/jsonb)."""
        self._query = self._query.contains(column, value)
        return self
    
    def order(self, column: str, desc: bool = False, **kwargs) -> "AsyncTableWrapper":
        """Order results by column."""
        self._query = self._query.order(column, desc=desc, **kwargs)
        return self
    
    def limit(self, count: int) -> "AsyncTableWrapper":
        """Limit number of results."""
        self._query = self._query.limit(count)
        return self
    
    def range(self, start: int, end: int) -> "AsyncTableWrapper":
        """Get a range of results."""
        self._query = self._query.range(start, end)
        return self
    
    def single(self) -> "AsyncTableWrapper":
        """Expect a single result."""
        self._query = self._query.single()
        return self
    
    def maybe_single(self) -> "AsyncTableWrapper":
        """Maybe get a single result."""
        self._query = self._query.maybe_single()
        return self
    
    async def execute(self):
        """
        Execute the query asynchronously.
        
        Returns:
            The query response object with .data, .count, etc.
        """
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, self._query.execute)
            return result
        except Exception as e:
            logger.error(f"Error executing Supabase query: {str(e)}")
            raise


# Initialize the synchronous Supabase client
try:
    _sync_client: Client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY
    )
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {e}")
    raise RuntimeError(
        f"Failed to initialize Supabase client: {e}. "
        "Please check SUPABASE_URL and SUPABASE_KEY environment variables."
    ) from e

# Create the async wrapper instance
supabase = AsyncSupabaseClient(_sync_client)

# Also export the sync client for cases where you need it
supabase_sync = _sync_client
