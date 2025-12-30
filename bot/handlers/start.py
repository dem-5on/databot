from telegram import Update
from telegram.ext import ContextTypes
from bot.keyboard import get_main_keyboard
from bot.api_client import telegram_api


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    telegram_id = str(user.id)
    
    # Check if there's a referral code in the command
    referral_code = None
    if update.message and update.message.text:
        parts = update.message.text.split()
        if len(parts) > 1:
            referral_code = parts[1]
    
    # Register user via backend with authentication
    try:
        user_data = await telegram_api.ensure_user(
            user_id=telegram_id,
            name=user.full_name or "",
            referral_code=referral_code
        )
        
        # Show referral message if new user was referred
        if referral_code and user_data.get("is_new_user"):
            await update.message.reply_text(
                f"🎉 Welcome! You were referred by someone using code: {referral_code}\n"
                "Complete your first transaction to activate their referral bonus!"
            )
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ Error connecting to backend. Please try again later.\n\nError: {str(e)}"
        )
        return
    
    welcome_text = (
        f"👋 Welcome to Intejers Data hub, {user.first_name}!\n\n"
        "Use the keyboard below to:\n"
        "➕ Deposit funds via Mobile Money\n"
        "💼 Check your wallet balance\n"
        "🌐 Browse and purchase data bundles\n"
        "📜 View transaction history\n"
        "🎯 Referral program - Earn rewards!\n"
        "❓ Get help\n\n"
        " ⚠️ IMPORTANT NOTICE:\n"

        "Turbonet and Broadband Sim Cards are not eligible for this offer.\n"

        "• Please do not place orders for the same number at the same time interval. One will be rejected and no refund will be provided.\n"

        "• Data bundle delivery is not instant. Some numbers may receive data faster while others take some time.\n"

        "• No refunds will be issued for wrong transactions or incorrect phone numbers.\n"

        "• Please verify your phone number carefully before making a purchase.\n\n"
        "Select an option from the menu:"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard()
    )
