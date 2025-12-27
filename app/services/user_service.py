import logging
from typing import Optional, Dict, Any, Tuple
from app.utils.phone_utils import normalize_phone_number
from app.repository.base_user_repo import BaseUserRepository
from app.repository.telegram_user_repo import TelegramUserRepository
from app.repository.whatsapp_user_repo import WhatsAppUserRepository
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)


class UserService:
    """Service for unified user management across platforms."""
    
    def __init__(self):
        self.base_user_repo = BaseUserRepository()
        self.telegram_user_repo = TelegramUserRepository()
        self.whatsapp_user_repo = WhatsAppUserRepository()
        self.referral_service = ReferralService()

    async def get_or_create_telegram_user(
        self,
        telegram_id: str,
        name: Optional[str] = None,
        referral_code: Optional[str] = None
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Get or create a Telegram user.
        
        Args:
            telegram_id: The Telegram user ID
            name: Optional user name
            referral_code: Optional referral code to register
            
        Returns:
            Tuple of (user_record, was_created)
            where was_created is True if a new user was created
        """
        try:
            # Check if Telegram user already exists
            telegram_user = await self.telegram_user_repo.get_by_telegram_id(telegram_id)
            
            if telegram_user:
                # User exists - get base user and update if needed
                user_id = telegram_user["user_id"]
                base_user = await self.base_user_repo.get_by_id(user_id)
                
                # Update name if provided
                if name and telegram_user.get("name") != name:
                    await self.telegram_user_repo.update_telegram_user(user_id, name=name)
                
                # Get full user data with platform info
                user_with_platforms = await self.base_user_repo.get_user_with_platforms(user_id)
                if user_with_platforms:
                    user_with_platforms["platform"] = "telegram"
                    return user_with_platforms, False
                
                # Fallback if get_user_with_platforms fails
                return {
                    **base_user,
                    "telegram_id": telegram_user["telegram_id"],
                    "phone": telegram_user.get("phone"),
                    "platform": "telegram"
                }, False
            else:
                # Create new base user
                base_user = await self.base_user_repo.create_base_user(name=name)
                user_id = base_user["id"]
                
                # Create Telegram user
                telegram_user, _ = await self.telegram_user_repo.get_or_create(
                    user_id=user_id,
                    telegram_id=telegram_id,
                    name=name
                )
                
                # Register referral if code provided
                if referral_code:
                    await self.referral_service.register_referral(user_id, referral_code)
                
                # Generate referral code for new user
                await self.referral_service.get_or_create_referral_code(user_id)
                
                # Return combined user data
                user_with_platforms = await self.base_user_repo.get_user_with_platforms(user_id)
                if user_with_platforms:
                    user_with_platforms["platform"] = "telegram"
                    return user_with_platforms, True
                
                # Fallback if get_user_with_platforms fails
                base_user = await self.base_user_repo.get_by_id(user_id)
                return {
                    **base_user,
                    "telegram_id": telegram_user["telegram_id"],
                    "phone": telegram_user.get("phone"),
                    "platform": "telegram"
                }, True
                
        except Exception as e:
            logger.error(f"Error in get_or_create_telegram_user: {str(e)}", exc_info=True)
            raise
    
    async def get_or_create_whatsapp_user(
        self,
        phone_number: str,
        name: Optional[str] = None,
        referral_code: Optional[str] = None
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Get or create a WhatsApp user.
        
        Args:
            phone_number: The WhatsApp phone number
            name: Optional user name
            referral_code: Optional referral code to register
            
        Returns:
            Tuple of (user_record, was_created)
            where was_created is True if a new user was created
        """
        try:
            # Normalize phone number
            normalized_phone = normalize_phone_number(phone_number)
            
            # Check if WhatsApp user already exists
            whatsapp_user = await self.whatsapp_user_repo.get_by_phone_number(normalized_phone)
            
            if whatsapp_user:
                # User exists - get base user and update if needed
                user_id = whatsapp_user["user_id"]
                base_user = await self.base_user_repo.get_by_id(user_id)
                
                # Update name if provided
                if name and whatsapp_user.get("name") != name:
                    await self.whatsapp_user_repo.update_whatsapp_user(user_id, name=name)
                
                # Get full user data with platform info
                user_with_platforms = await self.base_user_repo.get_user_with_platforms(user_id)
                if user_with_platforms:
                    user_with_platforms["platform"] = "whatsapp"
                    return user_with_platforms, False
                
                # Fallback if get_user_with_platforms fails
                return {
                    **base_user,
                    "phone": whatsapp_user["phone"],
                    "whatsapp_phone": whatsapp_user["phone"],
                    "platform": "whatsapp"
                }, False
            else:
                # Create new base user
                base_user = await self.base_user_repo.create_base_user(name=name)
                user_id = base_user["id"]
                
                # Create WhatsApp user
                whatsapp_user, _ = await self.whatsapp_user_repo.get_or_create(
                    user_id=user_id,
                    phone_number=normalized_phone,
                    name=name
                )
                
                # Register referral if code provided
                if referral_code:
                    await self.referral_service.register_referral(user_id, referral_code)
                
                # Generate referral code for new user
                await self.referral_service.get_or_create_referral_code(user_id)
                
                # Return combined user data
                user_with_platforms = await self.base_user_repo.get_user_with_platforms(user_id)
                if user_with_platforms:
                    user_with_platforms["platform"] = "whatsapp"
                    return user_with_platforms, True
                
                # Fallback if get_user_with_platforms fails
                base_user = await self.base_user_repo.get_by_id(user_id)
                return {
                    **base_user,
                    "phone": whatsapp_user["phone"],
                    "whatsapp_phone": whatsapp_user["phone"],
                    "platform": "whatsapp"
                }, True
                
        except Exception as e:
            logger.error(f"Error in get_or_create_whatsapp_user: {str(e)}", exc_info=True)
            raise
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by ID with platform information.
        
        Args:
            user_id: The user ID
            
        Returns:
            User record with platform information, or None if not found
        """
        return await self.base_user_repo.get_user_with_platforms(user_id)
    
    async def get_user_by_telegram_id(self, telegram_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by Telegram ID.
        
        Args:
            telegram_id: The Telegram user ID
            
        Returns:
            User record, or None if not found
        """
        telegram_user = await self.telegram_user_repo.get_by_telegram_id(telegram_id)
        if not telegram_user:
            return None
        
        return await self.get_user_by_id(telegram_user["user_id"])
    
    async def get_user_by_whatsapp_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Get user by WhatsApp phone number.
        
        Args:
            phone_number: The WhatsApp phone number (E.164 format)
            
        Returns:
            User record, or None if not found
        """
        normalized_phone = normalize_phone_number(phone_number)
        
        whatsapp_user = await self.whatsapp_user_repo.get_by_phone_number(normalized_phone)
        if not whatsapp_user:
            return None
        
        return await self.get_user_by_id(whatsapp_user["user_id"])
    
    async def link_telegram_whatsapp_accounts(
        self,
        telegram_id: str,
        phone_number: str
    ) -> Dict[str, Any]:
        """
        Link a Telegram account and WhatsApp account to the same base user.
        
        Args:
            telegram_id: The Telegram user ID
            phone_number: The WhatsApp phone number (E.164 format)
            
        Returns:
            Updated user record
        """
        normalized_phone = normalize_phone_number(phone_number)
        
        # Get existing users
        telegram_user = await self.telegram_user_repo.get_by_telegram_id(telegram_id)
        whatsapp_user = await self.whatsapp_user_repo.get_by_phone_number(normalized_phone)
        
        if telegram_user and whatsapp_user:
            # Both exist - merge them (keep telegram user's base_user)
            if telegram_user["user_id"] != whatsapp_user["user_id"]:
                # Update whatsapp_user to point to telegram_user's base_user
                await self.whatsapp_user_repo.update(whatsapp_user["id"], {
                    "user_id": telegram_user["user_id"]
                })
                # Delete orphaned base_user (if no other references)
                # Note: This is safe because foreign keys will cascade
                await self.base_user_repo.delete(whatsapp_user["user_id"])
            
            return await self.get_user_by_id(telegram_user["user_id"])
        elif telegram_user:
            # Telegram user exists, create WhatsApp user linked to same base_user
            await self.whatsapp_user_repo.create_whatsapp_user(
                user_id=telegram_user["user_id"],
                phone_number=normalized_phone
            )
            return await self.get_user_by_id(telegram_user["user_id"])
        elif whatsapp_user:
            # WhatsApp user exists, create Telegram user linked to same base_user
            await self.telegram_user_repo.create_telegram_user(
                user_id=whatsapp_user["user_id"],
                telegram_id=telegram_id
            )
            return await self.get_user_by_id(whatsapp_user["user_id"])
        else:
            # Neither exists, create new base_user with both platforms
            base_user = await self.base_user_repo.create_base_user()
            await self.telegram_user_repo.create_telegram_user(
                user_id=base_user["id"],
                telegram_id=telegram_id
            )
            await self.whatsapp_user_repo.create_whatsapp_user(
                user_id=base_user["id"],
                phone_number=normalized_phone
            )
            return await self.get_user_by_id(base_user["id"])

