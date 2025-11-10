import httpx
import logging
from app.core.config import settings
from app.utils.phone_utils import normalize_phone_number
from app.services.whatsapp_notifier import WhatsAppNotifierService

logger = logging.getLogger(__name__)


async def referral_handler(phone_number: str, bot) -> None:
    """
    Handle referral request.
    
    Args:
        phone_number: User's phone number
        bot: WhatsAppBot instance
    """
    try:
        normalized_phone = normalize_phone_number(phone_number)
        notifier = WhatsAppNotifierService()
        
        # Get user from database
        from app.services.user_service import UserService
        user_service = UserService()
        user = await user_service.get_user_by_whatsapp_phone(normalized_phone)
        
        if not user:
            await notifier.send_text_message(
                normalized_phone,
                "❌ User not found. Please start by typing 'hi' / 'start'."
            )
            return
        
        # Get referral code and stats from backend API
        try:
            async with httpx.AsyncClient() as client:
                # Get referral code
                code_response = await client.get(
                    f"{settings.BACKEND_API_URL}/api/v1/referrals/code/{normalized_phone}",
                    params={"identifier_type": "phone"},
                    timeout=10.0
                )
                code_response.raise_for_status()
                code_data = code_response.json()
                
                # Get referral stats
                stats_response = await client.get(
                    f"{settings.BACKEND_API_URL}/api/v1/referrals/referrals/{normalized_phone}",
                    params={"identifier_type": "phone"},
                    timeout=10.0
                )
                stats_response.raise_for_status()
                stats_data = stats_response.json()
                
                referral_code = code_data.get("referral_code", "N/A")
                total_referrals = stats_data.get("total_referrals", 0)
                referrals = stats_data.get("referrals", [])
                bonuses_paid = sum(1 for r in referrals if r.get("bonus_paid"))
                
                # Create referral message (WhatsApp doesn't support clickable links like Telegram)
                message = (
                    f"🎯 Your Referral Program\n\n"
                    f"📝 Your Referral Code: {referral_code}\n\n"
                    f"📊 Statistics:\n"
                    f"• Total Referrals: {total_referrals}\n"
                    f"• Bonuses Paid: {bonuses_paid}\n"
                    f"• Pending: {total_referrals - bonuses_paid}\n\n"
                    f"💰 How it works:\n"
                    f"• Share your referral code: {referral_code}\n"
                    f"• When someone uses your code and completes their first transaction (deposit or purchase),\n"
                    f"  you'll receive GHS {settings.REFERRAL_BONUS_AMOUNT} bonus!\n"
                    f"• The bonus is automatically added to your wallet balance.\n\n"
                    f"💡 Tip: Share your referral code to earn more rewards!"
                )
                
                await bot.send_main_menu(normalized_phone, message)
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get referral info: {e}")
            await bot.send_main_menu(
                normalized_phone,
                f"⚠️ Error fetching referral information\nPlease try again later."
            )
        except Exception as e:
            logger.error(f"Error in referral handler: {str(e)}", exc_info=True)
            await notifier.send_text_message(
                normalized_phone,
                "❌ An error occurred. Please try again later."
            )
            
    except Exception as e:
        logger.error(f"Unexpected error in referral handler: {str(e)}", exc_info=True)
        await notifier.send_text_message(
            normalized_phone,
            "❌ An error occurred. Please try again later."
        )

