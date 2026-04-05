import logging
from app.utils.phone_utils import normalize_phone_number
from app.services.whatsapp_notifier import WhatsAppNotifierService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


async def start_handler(phone_number: str, bot, referral_code: str = None) -> None:
    """
    Handle start command or initial message.
    
    Args:
        phone_number: User's phone number
        bot: WhatsAppBot instance
        referral_code: Optional referral code if provided by user
    """
    normalized_phone = normalize_phone_number(phone_number)
    notifier = WhatsAppNotifierService()

    try:
        # Call UserService directly — no HTTP self-call needed
        user_service = UserService()
        user_data, is_new_user = await user_service.get_or_create_whatsapp_user(
            phone_number=normalized_phone,
            name=None,  # WhatsApp doesn't provide name in webhook
            referral_code=referral_code,
        )

        # Handle referral code feedback
        if referral_code:
            if is_new_user:
                await notifier.send_text_message(
                    normalized_phone,
                    f"🎉 Welcome! You were referred by someone using code: {referral_code}\n"
                    f"Complete your first transaction to activate their referral bonus!"
                )
            else:
                await notifier.send_text_message(
                    normalized_phone,
                    "ℹ️ You're already registered. Referral codes can only be used when signing up for the first time."
                )

        if is_new_user:
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
                f"Working hours: 7am - 10pm\n\n"
                f"Select an option from the menu:"
            )
        else:
            welcome_text = (
                f"👋 Welcome back to Intejers Data hub!\n\n"
                f"Select an option from the menu:"
            )

        await bot.send_main_menu(normalized_phone, welcome_text)

    except Exception as e:
        logger.error(f"Unexpected error in start handler: {str(e)}", exc_info=True)
        await notifier.send_text_message(
            normalized_phone,
            "❌ Error connecting to server. Please try again later."
        )

