"""Repository for base user operations."""
import logging
from uuid import uuid4
from typing import Optional, Dict, Any
from app.repository.base import BaseRepository
from app.repository.telegram_user_repo import TelegramUserRepository
from app.repository.whatsapp_user_repo import WhatsAppUserRepository


logger = logging.getLogger(__name__)


class BaseUserRepository(BaseRepository):
    """Repository for base user operations (shared user data)."""
    
    def __init__(self):
        super().__init__("base_users")
    
    async def create_base_user(
        self,
        name: Optional[str] = None,
        referral_code: Optional[str] = None,
        referred_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new base user.
        
        Args:
            name: Optional user name
            referral_code: Optional referral code
            referred_by: Optional user ID who referred this user
            
        Returns:
            The created base user record
            
        Raises:
            ValueError: If creation fails
        """
        user_data = {
            "id": str(uuid4()),
            "name": name,
            "referral_code": referral_code,
            "referred_by": referred_by
        }
        
        try:
            user = await self.create(user_data)
            logger.info(f"Created base user with id: {user['id']}")
            return user
        except Exception as e:
            logger.error(f"Error creating base user: {str(e)}")
            raise
    
    async def update_base_user(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """
        Update a base user's information.
        
        Args:
            user_id: The user ID
            **kwargs: Fields to update
            
        Returns:
            The updated base user record
            
        Raises:
            ValueError: If update fails
        """
        try:
            # First check if user exists
            existing_user = await self.get_by_id(user_id)
            if not existing_user:
                raise ValueError(f"Base user {user_id} not found")
            
            # Update the user
            updated_user = await self.update(user_id, kwargs)
            logger.info(f"Updated base user {user_id} with fields: {list(kwargs.keys())}")
            return updated_user
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating base user {user_id}: {str(e)}")
            raise ValueError(f"Failed to update base user {user_id}: {str(e)}")
    
    async def get_user_with_platforms(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get base user with platform information (Telegram and WhatsApp).
        
        Args:
            user_id: The user ID
            
        Returns:
            User record with platform information, or None if not found
        """
        try:
            
            
            base_user = await self.get_by_id(user_id)
            if not base_user:
                return None
            
            # Get Telegram user if exists
            telegram_repo = TelegramUserRepository()
            telegram_user = await telegram_repo.get_by_user_id(user_id)
            
            # Get WhatsApp user if exists
            whatsapp_repo = WhatsAppUserRepository()
            whatsapp_user = await whatsapp_repo.get_by_user_id(user_id)
            
            # Combine data
            result = {
                **base_user,
                "telegram_id": telegram_user.get("telegram_id") if telegram_user else None,
                "phone": telegram_user.get("phone") if telegram_user else None,  # Telegram phone (if set)
                "whatsapp_phone": whatsapp_user.get("phone") if whatsapp_user else None,
                "platforms": []
            }
            
            if telegram_user:
                result["platforms"].append("telegram")
            if whatsapp_user:
                result["platforms"].append("whatsapp")
            
            # For backward compatibility, set "phone" to whatsapp_phone if available and no telegram phone
            if not result.get("phone") and result.get("whatsapp_phone"):
                result["phone"] = result["whatsapp_phone"]
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting user with platforms {user_id}: {str(e)}")
            return None

