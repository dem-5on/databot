"""Redis-backed state manager for WhatsApp bot conversations."""
import json
import logging
import redis
from typing import Dict, Tuple, Optional, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

# Default TTL for state (30 minutes)
DEFAULT_STATE_TTL = 1800


class InMemoryStateManager:
    """
    In-memory fallback state manager.
    
    Used when Redis is unavailable. Note: This only works in single-worker mode
    as state is not shared across workers.
    """
    
    def __init__(self):
        self._states: Dict[str, str] = {}
        self._data: Dict[str, Dict[str, Any]] = {}
        logger.warning("Using in-memory state manager (single-worker only)")
    
    def set_state(
        self, 
        phone_number: str, 
        state: str, 
        data: Optional[Dict[str, Any]] = None,
        ttl: int = DEFAULT_STATE_TTL
    ) -> None:
        self._states[phone_number] = state
        if data:
            self._data[phone_number] = data
    
    def get_state(self, phone_number: str) -> Tuple[str, Dict[str, Any]]:
        state = self._states.get(phone_number, "none")
        data = self._data.get(phone_number, {})
        return state, data
    
    def update_state_data(
        self, 
        phone_number: str, 
        ttl: int = DEFAULT_STATE_TTL,
        **kwargs
    ) -> None:
        if phone_number not in self._data:
            self._data[phone_number] = {}
        self._data[phone_number].update(kwargs)
    
    def clear_state(self, phone_number: str) -> None:
        self._states.pop(phone_number, None)
        self._data.pop(phone_number, None)
    
    def refresh_ttl(self, phone_number: str, ttl: int = DEFAULT_STATE_TTL) -> None:
        pass  # No-op for in-memory storage


class RedisStateManager:
    """
    Redis-backed state manager for conversation state storage.
    
    Enables multi-worker support by storing state in Redis instead of 
    in-memory dictionaries. States auto-expire after TTL to prevent
    stale data accumulation.
    
    Falls back to in-memory storage if Redis is unavailable.
    """
    
    _instance: Optional['RedisStateManager'] = None
    _client: Optional[redis.Redis] = None
    _fallback: Optional[InMemoryStateManager] = None
    _use_fallback: bool = False
    
    def __new__(cls):
        """Singleton pattern to reuse Redis connection."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Redis connection if not already connected."""
        if self._client is None and not self._use_fallback:
            self._connect()
    
    def _connect(self):
        """Establish Redis connection with fallback to in-memory."""
        try:
            # Use Celery broker URL (already configured for Redis)
            redis_url = settings.CELERY_BROKER_URL
            self._client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self._client.ping()
            logger.info("Redis state manager connected successfully")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using in-memory fallback.")
            self._use_fallback = True
            self._fallback = InMemoryStateManager()
    
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
        if self._use_fallback:
            self._fallback.set_state(phone_number, state, data, ttl)
            return
            
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
            # Fall back to in-memory on error
            if not self._use_fallback:
                self._use_fallback = True
                self._fallback = InMemoryStateManager()
                self._fallback.set_state(phone_number, state, data, ttl)
    
    def get_state(self, phone_number: str) -> Tuple[str, Dict[str, Any]]:
        """
        Get user conversation state.
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Tuple of (state, data)
        """
        if self._use_fallback:
            return self._fallback.get_state(phone_number)
            
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
        if self._use_fallback:
            self._fallback.update_state_data(phone_number, ttl, **kwargs)
            return
            
        try:
            state, data = self.get_state(phone_number)
            data.update(kwargs)
            self.set_state(phone_number, state, data, ttl)
            
            logger.debug(f"Updated Redis state data for {phone_number}: {list(kwargs.keys())}")
            
        except Exception as e:
            logger.error(f"Error updating Redis state data for {phone_number}: {e}")
    
    def clear_state(self, phone_number: str) -> None:
        """
        Clear user conversation state.
        
        Args:
            phone_number: User's phone number
        """
        if self._use_fallback:
            self._fallback.clear_state(phone_number)
            return
            
        try:
            state_key = self._get_key("state", phone_number)
            data_key = self._get_key("data", phone_number)
            
            self._client.delete(state_key, data_key)
            logger.debug(f"Cleared Redis state for {phone_number}")
            
        except Exception as e:
            logger.error(f"Error clearing Redis state for {phone_number}: {e}")
    
    def refresh_ttl(self, phone_number: str, ttl: int = DEFAULT_STATE_TTL) -> None:
        """
        Refresh TTL for user's state keys.
        
        Args:
            phone_number: User's phone number
            ttl: New time-to-live in seconds
        """
        if self._use_fallback:
            self._fallback.refresh_ttl(phone_number, ttl)
            return
            
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
