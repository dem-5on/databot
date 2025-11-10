"""Repository for WhatsApp user operations."""
import logging
from typing import Optional, Dict, Any, Tuple
from uuid import uuid4
from app.repository.base import BaseRepository

logger = logging.getLogger(__name__)


class WhatsAppUserRepository(BaseRepository):
    """Repository for WhatsApp user operations."""
    
    def __init__(self):
        super().__init__("whatsapp_users")
    
    async def get_by_phone_number(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Get WhatsApp user by phone number.
        
        Args:
            phone_number: The phone number (WhatsApp phone number in E.164 format)
            
        Returns:
            WhatsApp user record if found, None otherwise
        """
        return await self.get_by_field("phone", phone_number)
    
    async def get_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get WhatsApp user by base user ID.
        
        Args:
            user_id: The base user ID
            
        Returns:
            WhatsApp user record if found, None otherwise
        """
        return await self.get_by_field("user_id", user_id)
    
    async def create_whatsapp_user(
        self,
        user_id: str,
        phone_number: str,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new WhatsApp user.
        
        Args:
            user_id: The base user ID
            phone_number: The phone number (WhatsApp phone number in E.164 format)
            name: Optional user name
            
        Returns:
            The created WhatsApp user record
            
        Raises:
            ValueError: If creation fails
        """
        whatsapp_user_data = {
            "id": str(uuid4()),
            "user_id": user_id,
            "phone": phone_number,
            "name": name
        }
        
        try:
            whatsapp_user = await self.create(whatsapp_user_data)
            logger.info(f"Created WhatsApp user with phone: {phone_number}, user_id: {user_id}")
            return whatsapp_user
        except Exception as e:
            logger.error(f"Error creating WhatsApp user: {str(e)}")
            raise
    
    async def update_whatsapp_user(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """
        Update a WhatsApp user's information.
        
        Args:
            user_id: The base user ID (not whatsapp_user.id)
            **kwargs: Fields to update
            
        Returns:
            The updated WhatsApp user record
            
        Raises:
            ValueError: If update fails
        """
        try:
            # Find whatsapp_user by user_id
            whatsapp_user = await self.get_by_user_id(user_id)
            if not whatsapp_user:
                raise ValueError(f"WhatsApp user not found for user_id: {user_id}")
            
            # Update the whatsapp_user
            updated_whatsapp_user = await self.update(whatsapp_user["id"], kwargs)
            logger.info(f"Updated WhatsApp user {user_id} with fields: {list(kwargs.keys())}")
            return updated_whatsapp_user
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating WhatsApp user {user_id}: {str(e)}")
            raise ValueError(f"Failed to update WhatsApp user {user_id}: {str(e)}")
    
    async def get_or_create(
        self,
        user_id: str,
        phone_number: str,
        name: Optional[str] = None
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Get WhatsApp user by phone number or create if not exists.
        
        Args:
            user_id: The base user ID (must exist in base_users table)
            phone_number: The phone number (WhatsApp phone number in E.164 format)
            name: Optional user name
            
        Returns:
            Tuple of (whatsapp_user_record, was_created)
            where was_created is True if a new WhatsApp user was created
        """
        try:
            whatsapp_user = await self.get_by_phone_number(phone_number)
            
            if whatsapp_user:
                # WhatsApp user exists - update name if provided and different
                if name and whatsapp_user.get("name") != name:
                    try:
                        whatsapp_user = await self.update_whatsapp_user(whatsapp_user["user_id"], name=name)
                        logger.info(f"Updated name for phone_number {phone_number}")
                    except Exception as e:
                        logger.warning(f"Failed to update name for phone_number {phone_number}: {str(e)}")
                        # Return existing user even if name update fails
                
                return whatsapp_user, False
            else:
                # WhatsApp user doesn't exist - create new WhatsApp user
                whatsapp_user = await self.create_whatsapp_user(
                    user_id=user_id,
                    phone_number=phone_number,
                    name=name
                )
                return whatsapp_user, True
                
        except Exception as e:
            logger.error(f"Error in get_or_create for phone_number {phone_number}: {str(e)}")
            raise

