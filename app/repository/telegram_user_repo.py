import logging
from uuid import uuid4
from typing import Optional, Dict, Any, Tuple
from app.repository.base import BaseRepository

logger = logging.getLogger(__name__)


class TelegramUserRepository(BaseRepository):
    """Repository for Telegram user operations."""
    
    def __init__(self):
        super().__init__("telegram_users")
    
    async def get_by_telegram_id(self, telegram_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Telegram user by Telegram ID.
        
        Args:
            telegram_id: The Telegram user ID
            
        Returns:
            Telegram user record if found, None otherwise
        """
        return await self.get_by_field("telegram_id", telegram_id)
    
    async def get_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Telegram user by base user ID.
        
        Args:
            user_id: The base user ID
            
        Returns:
            Telegram user record if found, None otherwise
        """
        return await self.get_by_field("user_id", user_id)
    
    async def create_telegram_user(
        self,
        user_id: str,
        telegram_id: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new Telegram user.
        
        Args:
            user_id: The base user ID
            telegram_id: The Telegram user ID
            name: Optional user name
            phone: Optional phone number
            provider: Optional mobile money provider
            
        Returns:
            The created Telegram user record
            
        Raises:
            ValueError: If creation fails
        """
        telegram_user_data = {
            "id": str(uuid4()),
            "user_id": user_id,
            "telegram_id": telegram_id,
            "name": name,
            "phone": phone,
            "provider": provider
        }
        
        try:
            telegram_user = await self.create(telegram_user_data)
            logger.info(f"Created Telegram user with telegram_id: {telegram_id}, user_id: {user_id}")
            return telegram_user
        except Exception as e:
            logger.error(f"Error creating Telegram user: {str(e)}")
            raise
    
    async def update_telegram_user(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """
        Update a Telegram user's information.
        
        Args:
            user_id: The base user ID (not telegram_user.id)
            **kwargs: Fields to update
            
        Returns:
            The updated Telegram user record
            
        Raises:
            ValueError: If update fails
        """
        try:
            # Find telegram_user by user_id
            telegram_user = await self.get_by_user_id(user_id)
            if not telegram_user:
                raise ValueError(f"Telegram user not found for user_id: {user_id}")
            
            # Update the telegram_user using the telegram_user's id
            updated_telegram_user = await self.update(telegram_user["id"], kwargs)
            logger.info(f"Updated Telegram user {user_id} with fields: {list(kwargs.keys())}")
            return updated_telegram_user
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating Telegram user {user_id}: {str(e)}")
            raise ValueError(f"Failed to update Telegram user {user_id}: {str(e)}")
    
    async def get_or_create(
        self,
        user_id: str,
        telegram_id: str,
        name: Optional[str] = None
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Get Telegram user by Telegram ID or create if not exists.
        
        Args:
            user_id: The base user ID (must exist in base_users table)
            telegram_id: The Telegram user ID
            name: Optional user name
            
        Returns:
            Tuple of (telegram_user_record, was_created)
            where was_created is True if a new Telegram user was created
        """
        try:
            telegram_user = await self.get_by_telegram_id(telegram_id)
            
            if telegram_user:
                # Telegram user exists - update name if provided and different
                if name and telegram_user.get("name") != name:
                    try:
                        telegram_user = await self.update_telegram_user(telegram_user["user_id"], name=name)
                        logger.info(f"Updated name for telegram_id {telegram_id}")
                    except Exception as e:
                        logger.warning(f"Failed to update name for telegram_id {telegram_id}: {str(e)}")
                        # Return existing user even if name update fails
                
                return telegram_user, False
            else:
                # Telegram user doesn't exist - create new Telegram user
                telegram_user = await self.create_telegram_user(
                    user_id=user_id,
                    telegram_id=telegram_id,
                    name=name
                )
                return telegram_user, True
                
        except Exception as e:
            logger.error(f"Error in get_or_create for telegram_id {telegram_id}: {str(e)}")
            raise

