import logging
from uuid import uuid4
from typing import Optional, Dict, Any, Tuple
from app.repository.base import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    """Repository for user operations."""
    
    def __init__(self):
        super().__init__("base_users")
    
    async def get_by_telegram_id(self, telegram_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by Telegram ID.
        
        Args:
            telegram_id: The Telegram user ID
            
        Returns:
            User record if found, None otherwise
        """
        return await self.get_by_field("telegram_id", telegram_id)
    
    async def get_by_phone_number(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Get user by phone number.
        
        Args:
            phone_number: The phone number (WhatsApp phone number)
            
        Returns:
            User record if found, None otherwise
        """
        return await self.get_by_field("phone", phone_number)
    
    async def create_user(
        self, 
        telegram_id: Optional[str] = None,
        phone_number: Optional[str] = None,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new user.
        
        Args:
            telegram_id: The Telegram user ID (optional)
            phone_number: The phone number (optional, for WhatsApp)
            name: Optional user name
            
        Returns:
            The created user record
            
        Raises:
            ValueError: If user creation fails or neither telegram_id nor phone_number provided
        """
        if not telegram_id and not phone_number:
            raise ValueError("Either telegram_id or phone_number must be provided")
        
        user_data = {
            "id": str(uuid4()),
            "name": name
        }
        
        if telegram_id:
            user_data["telegram_id"] = telegram_id
        if phone_number:
            user_data["phone"] = phone_number
        
        try:
            user = await self.create(user_data)
            identifier = telegram_id or phone_number
            logger.info(f"Created user with identifier: {identifier}")
            return user
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise
    
    async def update_user(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """
        Update a user's information.
        
        Args:
            user_id: The user ID
            **kwargs: Fields to update
            
        Returns:
            The updated user record
            
        Raises:
            ValueError: If user not found or update fails
        """
        try:
            # First check if user exists
            existing_user = await self.get_by_id(user_id)
            if not existing_user:
                raise ValueError(f"User {user_id} not found")
            
            # Update the user
            updated_user = await self.update(user_id, kwargs)
            logger.info(f"Updated user {user_id} with fields: {list(kwargs.keys())}")
            return updated_user
            
        except ValueError:
            # Re-raise ValueError as is
            raise
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {str(e)}")
            raise ValueError(f"Failed to update user {user_id}: {str(e)}")
    
    async def update_user_name(self, user_id: str, name: str) -> Dict[str, Any]:
        """
        Update a user's name.
        
        Args:
            user_id: The user ID
            name: The new name
            
        Returns:
            The updated user record
        """
        return await self.update_user(user_id, name=name)
    
    async def update_phone_number(self, user_id: str, phone_number: str) -> Dict[str, Any]:
        """
        Update a user's phone number.
        
        Args:
            user_id: The user ID
            phone_number: The new phone number
            
        Returns:
            The updated user record
        """
        return await self.update_user(user_id, phone=phone_number)
    
    async def get_or_create(
        self, 
        telegram_id: str, 
        name: Optional[str] = None
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Get user by Telegram ID or create if not exists.
        
        Args:
            telegram_id: The Telegram user ID
            name: Optional user name
            
        Returns:
            Tuple of (user_record, was_created)
            where was_created is True if a new user was created
        """
        try:
            user = await self.get_by_telegram_id(telegram_id)
            
            if user:
                # User exists - update name if provided and different
                if name and user.get("name") != name:
                    try:
                        user = await self.update_user(user["id"], name=name)
                        logger.info(f"Updated name for telegram_id {telegram_id}")
                    except Exception as e:
                        logger.warning(f"Failed to update name for telegram_id {telegram_id}: {str(e)}")
                        # Return existing user even if name update fails
                
                return user, False
            else:
                # User doesn't exist - create new user
                user = await self.create_user(telegram_id, name)
                return user, True
                
        except Exception as e:
            logger.error(f"Error in get_or_create for telegram_id {telegram_id}: {str(e)}")
            raise
    
    async def get_all_users(self, limit: Optional[int] = None) -> list[Dict[str, Any]]:
        """
        Get all users.
        
        Args:
            limit: Optional limit on number of users to return
            
        Returns:
            List of user records
        """
        return await self.get_all(limit=limit, order_by="created_at", ascending=False)
    
    async def user_exists(self, telegram_id: str) -> bool:
        """
        Check if a user exists by Telegram ID.
        
        Args:
            telegram_id: The Telegram user ID
            
        Returns:
            True if user exists, False otherwise
        """
        user = await self.get_by_telegram_id(telegram_id)
        return user is not None
    
    async def get_or_create_by_phone(
        self,
        phone_number: str,
        name: Optional[str] = None
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Get user by phone number or create if not exists.
        
        Args:
            phone_number: The phone number (WhatsApp phone number)
            name: Optional user name
            
        Returns:
            Tuple of (user_record, was_created)
            where was_created is True if a new user was created
        """
        try:
            user = await self.get_by_phone_number(phone_number)
            
            if user:
                # User exists - update name if provided and different
                if name and user.get("name") != name:
                    try:
                        user = await self.update_user(user["id"], name=name)
                        logger.info(f"Updated name for phone_number {phone_number}")
                    except Exception as e:
                        logger.warning(f"Failed to update name for phone_number {phone_number}: {str(e)}")
                        # Return existing user even if name update fails
                
                return user, False
            else:
                # User doesn't exist - create new user
                user = await self.create_user(phone_number=phone_number, name=name)
                return user, True
                
        except Exception as e:
            logger.error(f"Error in get_or_create_by_phone for phone_number {phone_number}: {str(e)}")
            raise
    
    async def delete_user(self, user_id: str) -> bool:
        """
        Delete a user.
        
        WARNING: This will also affect related records (wallet, orders, etc.)
        depending on your database constraints.
        
        Args:
            user_id: The user ID
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If deletion fails
        """
        try:
            user = await self.get_by_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            await self.delete(user_id)
            logger.info(f"Deleted user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {str(e)}")
            raise
    
    async def search_users_by_name(self, name_query: str, limit: int = 10) -> list[Dict[str, Any]]:
        """
        Search users by name (case-insensitive partial match).
        
        Args:
            name_query: The name to search for
            limit: Maximum number of results
            
        Returns:
            List of matching user records
        """
        try:
            response = await (
                self.client.table(self.table_name)
                .select("*")
                .ilike("name", f"%{name_query}%")
                .limit(limit)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error searching users by name '{name_query}': {str(e)}")
            return []