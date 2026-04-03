import logging
from app.utils.phone_utils import normalize_phone_number
from app.services.whatsapp_notifier import WhatsAppNotifierService

logger = logging.getLogger(__name__)


async def help_handler(phone_number: str, bot) -> None:
    """
    Handle help request.
    
    Args:
        phone_number: User's phone number
        bot: WhatsAppBot instance
    """
    try:
        normalized_phone = normalize_phone_number(phone_number)
        notifier = WhatsAppNotifierService()
        
        help_text = (
            "❓ Help & Support\n\n"
            "💼 Features:\n"
            "• Balance - Check your wallet balance\n"
            "• Deposit - Add funds via Mobile Money\n"
            "• Bundles - Browse and purchase data bundles\n"
            "• History - View transaction and order history\n"
            "• Referral - View your referral code and stats\n\n"
            "📱 Supported Networks:\n"
            "• MTN\n"
            "• Telecel (Vodafone)\n"
            "• AirtelTigo\n\n"
            "💰 Payment Methods:\n"
            "• Mobile Money (MTN, Telecel, AirtelTigo)\n\n"
            "⚠️ IMPORTANT NOTICE:\n\n"
            "• Please do not place orders for the same number at the same time interval. One will be rejected and no refund will be provided.\n\n"
            "• Data bundle delivery is not instant. Some numbers may receive data faster while others take some time.\n\n"
            "• No refunds will be issued for wrong transactions or incorrect phone numbers.\n\n"
            "• Please verify your phone number carefully before making a purchase.\n\n"
            "Working hours: 7am - 10pm\n\n"
            "❓ Need more help?\n"
            "Contact the admin/support for assistance.\n"
            "WhatsApp: https://wa.me/message/M34LEOVGZGOZP1\n"
            "Telegram: https://t.me/intejsupport\n"
            "Phone: +233559457645"
        )
        
        await bot.send_main_menu(normalized_phone, help_text)
        
    except Exception as e:
        logger.error(f"Error in help handler: {str(e)}", exc_info=True)
        await notifier.send_text_message(
            normalized_phone,
            "❌ An error occurred. Please try again later."
        )

