"""Redis-backed state manager for WhatsApp bot conversations."""
import json
import logging
import redis
from typing import Dict, Tuple, Optional, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

# Default TTL for state (30 minutes)
DEFAULT_STATE_TTL = 1800


class RedisStateManager:
    """
    Redis-backed state manager for conversation state storage.
    
    Enables multi-worker support by storing state in Redis instead of 
    in-memory dictionaries. States auto-expire after TTL to prevent
    stale data accumulation.
    """
    
    _instance: Optional['RedisStateManager'] = None
    _client: Optional[redis.Redis] = None
    
    def __new__(cls):
        """Singleton pattern to reuse Redis connection."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Redis connection if not already connected."""
        if self._client is None:
            self._connect()
    
    def _connect(self):
        """Establish Redis connection."""
        try:
            # Use Celery broker URL (already configured for Redis)
            redis_url = settings.CELERY_BROKER_URL
            self._client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self._client.ping()
            logger.info("Redis state manager connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def _get_key(self, prefix: str, phone_number: str) -> str:
        """Generate Redis key for a phone number."""
        return f"whatsapp_state:{prefix}:{phone_number}"
    
    def set_state(
        self, 
        phone_number: str, 
        state: str, 
        data: Optional[Dict[str, Any]] = None,
        ttl: int = DEFAULT_STATE_TTL
    ) -> None:
        """
        Set user conversation state.
        
        Args:
            phone_number: User's phone number
            state: State name
            data: Optional state data
            ttl: Time-to-live in seconds (default: 30 minutes)
        """
        try:
            state_key = self._get_key("state", phone_number)
            data_key = self._get_key("data", phone_number)
            
            # Set state
            self._client.setex(state_key, ttl, state)
            
            # Set data (as JSON)
            if data:
                self._client.setex(data_key, ttl, json.dumps(data))
            
            logger.debug(f"Set Redis state for {phone_number}: {state}")
            
        except Exception as e:
            logger.error(f"Error setting Redis state for {phone_number}: {e}")
            raise
    
    def get_state(self, phone_number: str) -> Tuple[str, Dict[str, Any]]:
        """
        Get user conversation state.
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Tuple of (state, data)
        """
        try:
            state_key = self._get_key("state", phone_number)
            data_key = self._get_key("data", phone_number)
            
            state = self._client.get(state_key) or "none"
            data_json = self._client.get(data_key)
            data = json.loads(data_json) if data_json else {}
            
            return state, data
            
        except Exception as e:
            logger.error(f"Error getting Redis state for {phone_number}: {e}")
            return "none", {}
    
    def update_state_data(
        self, 
        phone_number: str, 
        ttl: int = DEFAULT_STATE_TTL,
        **kwargs
    ) -> None:
        """
        Update user state data without changing state.
        
        Args:
            phone_number: User's phone number
            ttl: Time-to-live in seconds
            **kwargs: Data to update
        """
        try:
            state, data = self.get_state(phone_number)
            data.update(kwargs)
            self.set_state(phone_number, state, data, ttl)
            
            logger.debug(f"Updated Redis state data for {phone_number}: {list(kwargs.keys())}")
            
        except Exception as e:
            logger.error(f"Error updating Redis state data for {phone_number}: {e}")
            raise
    
    def clear_state(self, phone_number: str) -> None:
        """
        Clear user conversation state.
        
        Args:
            phone_number: User's phone number
        """
        try:
            state_key = self._get_key("state", phone_number)
            data_key = self._get_key("data", phone_number)
            
            self._client.delete(state_key, data_key)
            logger.debug(f"Cleared Redis state for {phone_number}")
            
        except Exception as e:
            logger.error(f"Error clearing Redis state for {phone_number}: {e}")
            raise
    
    def refresh_ttl(self, phone_number: str, ttl: int = DEFAULT_STATE_TTL) -> None:
        """
        Refresh TTL for user's state keys.
        
        Args:
            phone_number: User's phone number
            ttl: New time-to-live in seconds
        """
        try:
            state_key = self._get_key("state", phone_number)
            data_key = self._get_key("data", phone_number)
            
            self._client.expire(state_key, ttl)
            self._client.expire(data_key, ttl)
            
        except Exception as e:
            logger.error(f"Error refreshing TTL for {phone_number}: {e}")


# Singleton instance for easy import
_state_manager: Optional[RedisStateManager] = None


def get_state_manager() -> RedisStateManager:
    """Get the singleton Redis state manager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = RedisStateManager()
    return _state_manager
