import httpx
import logging
from app.core.config import settings
from app.services.user_service import UserService
from app.utils.backend_client import BackendAPIClient
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
        user_service = UserService()
        user = await user_service.get_user_by_whatsapp_phone(normalized_phone)
        
        if not user:
            await notifier.send_text_message(
                normalized_phone,
                "❌ User not found. Please start by typing 'hi' / 'start'."
            )
            return
        
        # Get authentication headers
        headers = BackendAPIClient.get_auth_headers(normalized_phone, "whatsapp")
        
        # Get referral code and stats from backend API with retry logic
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                client = BackendAPIClient.get_client()
                
                # Get referral code
                code_response = await client.get(
                    f"{settings.BACKEND_API_URL}/api/v1/referrals/code/{normalized_phone}",
                    params={"identifier_type": "phone"},
                    headers=headers,
                )
                code_response.raise_for_status()
                code_data = code_response.json()
                
                # Get referral stats
                stats_response = await client.get(
                    f"{settings.BACKEND_API_URL}/api/v1/referrals/referrals/{normalized_phone}",
                    params={"identifier_type": "phone"},
                    headers=headers,
                )
                stats_response.raise_for_status()
                stats_data = stats_response.json()
                break  # Success
            except (httpx.RemoteProtocolError, httpx.ConnectError) as conn_error:
                if attempt < max_retries:
                    logger.warning(f"Connection error (attempt {attempt + 1}/{max_retries + 1}), resetting client: {conn_error}")
                    await BackendAPIClient.reset_client()
                else:
                    raise
        
        referral_code = code_data.get("referral_code", "N/A")
        total_referrals = stats_data.get("total_referrals", 0)
        referrals = stats_data.get("referrals", [])
        bonuses_paid = sum(1 for r in referrals if r.get("bonus_paid"))
        
        # Create WhatsApp referral link
        business_phone = settings.WHATSAPP_BUSINESS_PHONE.replace("+", "").replace(" ", "").replace("-", "")
        referral_link = f"https://wa.me/{business_phone}?text=start={referral_code}"
        
        # Create referral message with both code and link
        message = (
            f"🎯 Your Referral Program\n\n"
            f"📝 Your Referral Code: {referral_code}\n\n"
            f"🔗 Your Referral Link:\n{referral_link}\n\n"
            f"📊 Statistics:\n"
            f"• Total Referrals: {total_referrals}\n"
            f"• Bonuses Paid: {bonuses_paid}\n"
            f"• Pending: {total_referrals - bonuses_paid}\n\n"
            f"💰 How it works:\n"
            f"• Share your referral link with friends\n"
            f"• When they complete their first transaction (deposit or purchase),\n"
            f"  you'll receive GHS {settings.REFERRAL_BONUS_AMOUNT} bonus!\n"
            f"• The bonus is automatically added to your wallet balance.\n\n"
            f"💡 Tip: Share your referral link to earn more rewards!"
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
