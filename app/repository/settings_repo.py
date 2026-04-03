import logging
from typing import Optional, List, Dict, Any
from app.repository.base import BaseRepository

logger = logging.getLogger(__name__)


class SettingsRepository(BaseRepository):
    """Repository for system settings."""
    
    def __init__(self):
        super().__init__("system_settings")
    
    async def get_setting(self, key: str) -> Optional[Any]:
        """Get a setting value by key."""
        record = await self.get_by_field("key", key)
        return record.get("value") if record else None
    
    async def set_setting(self, key: str, value: Any, description: str = None) -> Dict[str, Any]:
        """Set a setting value."""
        existing = await self.get_by_field("key", key)
        
        data = {
            "key": key,
            "value": value
        }
        if description:
            data["description"] = description
            
        if existing:
            return await self.update(existing["id"], data)
        else:
            # Need ID for new record
            from uuid import uuid4
            data["id"] = str(uuid4())
            return await self.create(data)
            
    async def get_all_settings(self) -> List[Dict[str, Any]]:
        """Get all settings."""
        return await self.get_all(order_by="key")

    async def update_settings_bulk(self, settings_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update multiple settings at once."""
        updated = []
        for key, value in settings_dict.items():
            try:
                res = await self.set_setting(key, value)
                updated.append(res)
            except Exception as e:
                logger.error(f"Failed to update setting {key}: {e}")
        return updated
