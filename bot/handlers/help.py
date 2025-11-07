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
        "• Vodafone\n"
        "• AirtelTigo\n\n"
        "💰 Payment Methods:\n"
        "• Mobile Money (MTN, Vodafone, AirtelTigo)\n\n"
        "❓ Need more help?\n\n"
        " ⚠️ IMPORTANT NOTICE:\n"

        "Turbonet and Broadband Sim Cards are not eligible for this offer."

        "• Please do not place orders for the same number at the same time interval. One will be rejected and no refund will be provided."

        "• Data bundle delivery is not instant. Some numbers may receive data faster while others take some time."

        "• No refunds will be issued for wrong transactions or incorrect phone numbers."

        "• Please verify your phone number carefully before making a purchase.\n\n"
        "Contact the admin for assistance.\n"
        "Help Bot: @tex_tar_bot"
    )
    
    await update.message.reply_text(help_text)

