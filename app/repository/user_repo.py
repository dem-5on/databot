from typing import Optional, Dict, Any
from uuid import uuid4
from app.repository.base import BaseRepository


class UserRepository(BaseRepository):
    """Repository for user operations."""
    
    def __init__(self):
        super().__init__("users")
    
    def get_by_telegram_id(self, telegram_id: str) -> Optional[Dict[str, Any]]:
        """Get user by Telegram ID."""
        return self.get_by_field("telegram_id", telegram_id)
    
    def create_user(self, telegram_id: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new user."""
        user_data = {
            "id": str(uuid4()),
            "telegram_id": telegram_id,
            "name": name
        }
        return self.create(user_data)
    
    def update_user(self, user_id: str, **kwargs) -> dict:
        try:
            updated_user = self.update(user_id, kwargs)
            if not updated_user:
                raise ValueError(f"User {user_id} not found")
            return updated_user
        except Exception as e:
            raise ValueError(f"Failed to update user {user_id}: {str(e)}")
            
    def get_or_create(self, telegram_id: str, name: Optional[str] = None) -> tuple:
        """Get user by Telegram ID or create if not exists."""
        user = self.get_by_telegram_id(telegram_id)
        if user:
            # Update name if provided and different
            if name and user.get("name") != name:
                user = self.update_user(user["id"], name=name)
            return user, False
        else:
            user = self.create_user(telegram_id, name)
            return user, True
