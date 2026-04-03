import logging
import asyncio
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# Default lock timeout in seconds
DEFAULT_LOCK_TIMEOUT = 30

# Default retry settings
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY = 0.5  # seconds


class DistributedLock:
    """
    Redis-based distributed lock using SET NX with expiration.
    
    Usage:
        async with DistributedLock("wallet:user123"):
            # Critical section - only one worker can execute this
            await credit_wallet(...)
    """
    
    def __init__(
        self,
        lock_key: str,
        timeout: int = DEFAULT_LOCK_TIMEOUT,
        retry_count: int = DEFAULT_RETRY_COUNT,
        retry_delay: float = DEFAULT_RETRY_DELAY
    ):
        """
        Initialize a distributed lock.
        
        Args:
            lock_key: Unique identifier for what's being locked (e.g., "wallet:user_id")
            timeout: Lock expiration in seconds (prevents deadlocks)
            retry_count: Number of times to retry acquiring lock
            retry_delay: Delay between retries in seconds
        """
        self.lock_key = f"lock:{lock_key}"
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self._redis = None
        self._lock_value = None
    
    async def _get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                from app.core.config import settings
                
                # Parse Redis URL from Celery broker URL
                redis_url = settings.CELERY_BROKER_URL
                self._redis = redis.from_url(redis_url, decode_responses=True)
            except ImportError:
                logger.warning("redis package not available, using fallback lock")
                return None
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                return None
        return self._redis
    
    async def acquire(self) -> bool:
        """
        Attempt to acquire the lock.
        
        Returns:
            True if lock acquired, False otherwise
        """
        import uuid
        
        redis_client = await self._get_redis()
        if redis_client is None:
            # Fallback: no Redis available, allow operation (log warning)
            logger.warning(f"No Redis available for lock {self.lock_key}, proceeding without lock")
            return True
        
        self._lock_value = str(uuid.uuid4())
        
        for attempt in range(self.retry_count):
            try:
                # SET NX with expiration - atomic operation
                acquired = await redis_client.set(
                    self.lock_key,
                    self._lock_value,
                    nx=True,  # Only set if not exists
                    ex=self.timeout
                )
                
                if acquired:
                    logger.debug(f"Acquired lock: {self.lock_key}")
                    return True
                
                # Lock is held by another process, wait and retry
                if attempt < self.retry_count - 1:
                    await asyncio.sleep(self.retry_delay)
                    
            except Exception as e:
                logger.error(f"Error acquiring lock {self.lock_key}: {e}")
                if attempt < self.retry_count - 1:
                    await asyncio.sleep(self.retry_delay)
        
        logger.warning(f"Failed to acquire lock after {self.retry_count} attempts: {self.lock_key}")
        return False
    
    async def release(self) -> bool:
        """
        Release the lock if we own it.
        
        Uses Lua script to ensure we only release our own lock.
        
        Returns:
            True if lock released, False otherwise
        """
        redis_client = await self._get_redis()
        if redis_client is None or self._lock_value is None:
            return True
        
        # Lua script: only delete if we own the lock
        release_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        try:
            result = await redis_client.eval(
                release_script,
                1,  # number of keys
                self.lock_key,
                self._lock_value
            )
            
            if result == 1:
                logger.debug(f"Released lock: {self.lock_key}")
                return True
            else:
                logger.warning(f"Lock not released (not owned or expired): {self.lock_key}")
                return False
                
        except Exception as e:
            logger.error(f"Error releasing lock {self.lock_key}: {e}")
            return False
    
    async def __aenter__(self):
        """Async context manager entry."""
        acquired = await self.acquire()
        if not acquired:
            raise LockAcquisitionError(f"Could not acquire lock: {self.lock_key}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.release()
        return False  # Don't suppress exceptions


class LockAcquisitionError(Exception):
    """Raised when a lock cannot be acquired."""
    pass


@asynccontextmanager
async def wallet_lock(user_id: str, operation: str = "credit"):
    """
    Convenience function for locking wallet operations.
    
    Args:
        user_id: The user ID whose wallet is being modified
        operation: Type of operation (credit, debit, etc.)
        
    Usage:
        async with wallet_lock(user_id, "credit"):
            await wallet_service.credit_wallet(...)
    """
    lock_key = f"wallet:{operation}:{user_id}"
    lock = DistributedLock(lock_key, timeout=30, retry_count=5, retry_delay=0.3)
    
    try:
        acquired = await lock.acquire()
        if not acquired:
            raise LockAcquisitionError(
                "Wallet operation in progress. Please try again in a moment."
            )
        yield lock
    finally:
        await lock.release()


@asynccontextmanager
async def transaction_lock(reference: str):
    """
    Convenience function for locking transaction processing.
    
    Args:
        reference: Transaction reference
        
    Usage:
        async with transaction_lock(reference):
            await process_transaction(...)
    """
    lock_key = f"transaction:{reference}"
    lock = DistributedLock(lock_key, timeout=60, retry_count=3, retry_delay=1.0)
    
    try:
        acquired = await lock.acquire()
        if not acquired:
            raise LockAcquisitionError(
                "Transaction already being processed."
            )
        yield lock
    finally:
        await lock.release()
