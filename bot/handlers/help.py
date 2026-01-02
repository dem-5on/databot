from telegram import Update
from telegram.ext import ContextTypes


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle help command."""
    help_text = (
        "❓ Help & Support\n\n"
        "📋 Available Commands:\n"
        "• /start - Start the bot and register\n\n"
        "💼 Features:\n"
        "• Balance - Check your wallet balance\n"
        "• Deposit - Add funds via Mobile Money\n"
        "• Bundles - Browse and purchase data bundles\n"
        "• History - View transaction and order history\n\n"
        "📱 Supported Networks:\n"
        "• MTN\n"
        "• Telecel\n"
        "• AirtelTigo\n\n"
        "💰 Payment Methods:\n"
        "• Mobile Money (MTN, Telecel, AirtelTigo)\n\n"
        " ⚠️ IMPORTANT NOTICE:\n\n"
        "• Please do not place orders for the same number at the same time interval. One will be rejected and no refund will be provided.\n\n"

        "• Data bundle delivery is not instant. Some numbers may receive data faster while others take some time.\n\n"

        "• No refunds will be issued for wrong transactions or incorrect phone numbers.\n\n"

        "• Please verify your phone number carefully before making a purchase.\n\n"
        "❓ Need more help?\n"
        "Contact the admin/support for assistance.\n"
        "WhatsApp: https://wa.me/message/M34LEOVGZGOZP1\n"
        "Telegram: https://t.me/intejsupport\n"
        "Phone: +233559457645"
    )
    
    await update.message.reply_text(help_text)

