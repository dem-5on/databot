import httpx
from app.core.config import settings


class NotifierService:
    """Service for sending Telegram notifications."""

    TELEGRAM_API_URL = settings.TELEGRAM_API_URL

    @staticmethod
    async def send_user_message(telegram_id: int, text: str) -> bool:
        """
        Send a message to a user via Telegram.
        
        Args:
            telegram_id: User's Telegram ID
            text: Message text
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{NotifierService.TELEGRAM_API_URL}{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": telegram_id,
                "text": text,
                "parse_mode": "HTML"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()
                return True
        except Exception as e:
            print(f"Failed to send message to user {telegram_id}: {str(e)}")
            return False

    @staticmethod
    async def send_admin_alert(text: str) -> bool:
        """
        Send an alert to all admin Telegram IDs.
        
        Args:
            text: Alert message text
            
        Returns:
            True if sent to at least one admin, False otherwise
        """
        admin_ids = settings.admin_ids_list
        
        if not admin_ids:
            print("No admin IDs configured")
            return False
        
        success = False
        for admin_id in admin_ids:
            if await NotifierService.send_user_message(admin_id, text):
                success = True
        
        return success

