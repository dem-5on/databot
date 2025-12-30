import httpx
import logging
from app.core.config import settings
from app.utils.phone_utils import normalize_phone_number
from app.services.whatsapp_notifier import WhatsAppNotifierService
from bot.api_client import get_auth_headers

logger = logging.getLogger(__name__)


async def start_handler(phone_number: str, bot, referral_code: str = None) -> None:
    """
    Handle start command or initial message.
    
    Args:
        phone_number: User's phone number
        bot: WhatsAppBot instance
        referral_code: Optional referral code if provided by user
    """
    try:
        normalized_phone = normalize_phone_number(phone_number)
        notifier = WhatsAppNotifierService()
        
        # Register user via backend API
        try:
            async with httpx.AsyncClient() as client:
                request_data = {
                    "phone_number": normalized_phone,
                    "name": None  # WhatsApp doesn't provide name in webhook
                }
                
                # Add referral code if provided
                if referral_code:
                    request_data["referral_code"] = referral_code
                
                # Include authentication headers
                headers = get_auth_headers(normalized_phone, "whatsapp")
                
                response = await client.post(
                    f"{settings.BACKEND_API_URL}/api/v1/users/ensure-whatsapp",
                    json=request_data,
                    headers=headers,
                    timeout=10.0
                )
                response.raise_for_status()
                user_data = response.json()
                
                is_new_user = user_data.get("is_new_user", False)
                
                # Handle referral code feedback
                if referral_code:
                    if is_new_user:
                        # New user with referral code - show welcome message
                        await notifier.send_text_message(
                            normalized_phone,
                            f"🎉 Welcome! You were referred by someone using code: {referral_code}\n"
                            f"Complete your first transaction to activate their referral bonus!"
                        )
                    else:
                        # Existing user trying to use referral code - inform them
                        await notifier.send_text_message(
                            normalized_phone,
                            f"ℹ️ You're already registered. Referral codes can only be used when signing up for the first time."
                        )
                
                if is_new_user:
                    # Send welcome message for new users
                    welcome_text = (
                        f"👋 Welcome to Intejers Data Hub!\n\n"
                        f"Use the menu below to:\n"
                        f"💼 Check your wallet balance\n"
                        f"➕ Deposit funds via Mobile Money\n"
                        f"🌐 Browse and purchase data bundles\n"
                        f"📜 View transaction history\n"
                        f"🎯 Referral program - Earn rewards!\n"
                        f"❓ Get help\n\n"
                        f"⚠️ IMPORTANT NOTICE:\n\n"
                        f"• Turbonet and Broadband Sim Cards are not eligible for this offer.\n\n"
                        f"• Please do not place orders for the same number at the same time interval. One will be rejected and no refund will be provided.\n\n"
                        f"• Data bundle delivery is not instant. Some numbers may receive data faster while others take some time.\n\n"
                        f"• No refunds will be issued for wrong transactions or incorrect phone numbers.\n\n"
                        f"• Please verify your phone number carefully before making a purchase.\n\n"
                        f"Select an option from the menu:"
                    )
                else:
                    # Welcome back message
                    welcome_text = (
                        f"👋 Welcome back to Intejers Data hub!\n\n"
                        f"Select an option from the menu:"
                    )
                
                # Send main menu buttons via bot helper (includes both rows)
                await bot.send_main_menu(normalized_phone, welcome_text)
                
                # Clear any existing state
                # bot.clear_user_state(normalized_phone)
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to register user: {e}")
            try:
                error_detail = e.response.json()
                logger.error(f"Response body: {error_detail}")
            except Exception as json_error:
                logger.warning(f"Failed to parse error response JSON: {json_error}")
                logger.error(f"Response text: {e.response.text}")
            
            await notifier.send_text_message(
                normalized_phone,
                "❌ Error connecting to server. Please try again later."
            )
            
    except Exception as e:
        logger.error(f"Unexpected error in start handler: {str(e)}", exc_info=True)

