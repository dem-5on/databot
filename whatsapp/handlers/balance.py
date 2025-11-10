import httpx
import logging
from app.core.config import settings
from app.utils.phone_utils import normalize_phone_number
from app.services.whatsapp_notifier import WhatsAppNotifierService
from app.services.wallet_service import WalletService
from app.repository.user_repo import UserRepository

logger = logging.getLogger(__name__)


async def balance_handler(phone_number: str, bot) -> None:
    """
    Handle balance check request.
    
    Args:
        phone_number: User's phone number
        bot: WhatsAppBot instance
    """
    try:
        normalized_phone = normalize_phone_number(phone_number)
        notifier = WhatsAppNotifierService()
        
        # Get user by phone number
        from app.services.user_service import UserService
        user_service = UserService()
        user = await user_service.get_user_by_whatsapp_phone(normalized_phone)
        
        if not user:
            await notifier.send_text_message(
                normalized_phone,
                "❌ User not found. Please start by typing 'hi' or 'start'."
            )
            return
        
        # Get balance from backend API
        try:
            async with httpx.AsyncClient() as client:
                # Use phone number to get balance
                wallet_service = WalletService()
                balance = await wallet_service.get_balance(user["id"])
                
                balance_text = (
                    f"💼 Your Wallet Balance\n\n"
                    f"Amount: GHS {balance}\n\n"
                    f"Use the menu to deposit funds or purchase bundles."
                )
                
                await bot.send_main_menu(normalized_phone, balance_text)
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get balance: {e}")
            await notifier.send_text_message(
                normalized_phone,
                "⚠️ Failed to get balance. Please try again later."
            )
        except Exception as e:
            logger.error(f"Error in balance handler: {str(e)}", exc_info=True)
            await notifier.send_text_message(
                normalized_phone,
                "⚠️ Failed to get balance. Please try again later."
            )
            
    except Exception as e:
        logger.error(f"Unexpected error in balance handler: {str(e)}", exc_info=True)
        await notifier.send_text_message(
            normalized_phone,
            "❌ An error occurred. Please try again later."
        )

