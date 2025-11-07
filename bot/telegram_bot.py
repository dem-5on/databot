import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

from app.core.config import settings
from bot.handlers.start import start_command
from bot.handlers.balance import balance_handler
from bot.handlers.deposit import (
    deposit_start,
    deposit_amount,
    deposit_phone,
    deposit_cancel,
    deposit_otp,
    AMOUNT,
    PHONE,
    OTP
)
from bot.handlers.bundles import (
    bundles_start,
    bundles_network,
    bundles_bundle,
    bundles_phone,
    bundles_cancel,
    BUNDLES_NETWORK,
    BUNDLES_BUNDLE,
    BUNDLES_PHONE
)
from bot.handlers.history import history_handler
from bot.handlers.help import help_handler
from bot.handlers.referral import referral_command


async def handle_keyboard_button_exit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle keyboard button press to exit conversation and route to appropriate handler."""
    # Clear conversation data
    context.user_data.clear()
    
    # Get the button text
    message_text = update.message.text.strip() if update.message else ""
    
    # Route to appropriate handler based on button
    if message_text == "💼 Balance":
        await balance_handler(update, context)
    elif message_text == "📜 History":
        await history_handler(update, context)
    elif message_text == "🎯 Referral":
        await referral_command(update, context)
    elif message_text == "❓ Help":
        await help_handler(update, context)
    # Note: "➕ Deposit" and "🌐 Bundles" will start new conversations, handled by entry points
    
    return ConversationHandler.END

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def setup_handlers(application: Application):
    """Set up all bot handlers."""
    
    # Create filter to exclude keyboard buttons from conversation states
    keyboard_button_filter = filters.Regex("^(💼 Balance|➕ Deposit|🌐 Bundles|📜 History|🎯 Referral|❓ Help)$")
    not_keyboard_button = ~keyboard_button_filter
    
    # Command handlers (highest priority)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("referral", referral_command))
    
    # Conversation handler for deposits
    # Exclude keyboard buttons from state handlers so they can exit conversations
    deposit_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Deposit$"), deposit_start)],
        states={
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND & not_keyboard_button, deposit_amount)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND & not_keyboard_button, deposit_phone)],
            OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND & not_keyboard_button, deposit_otp)],
        },
        fallbacks=[
            CommandHandler("cancel", deposit_cancel),
            # Allow keyboard buttons to exit conversation and route to appropriate handler
            MessageHandler(keyboard_button_filter, handle_keyboard_button_exit),
        ],
    )
    application.add_handler(deposit_conv)
    
    # Conversation handler for bundles
    bundles_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🌐 Bundles$"), bundles_start)],
        states={
            BUNDLES_NETWORK: [
                CallbackQueryHandler(bundles_network, pattern="^(network:|cancel:bundles)")
            ],
            BUNDLES_BUNDLE: [
                CallbackQueryHandler(bundles_bundle, pattern="^(bundle:|back:networks|cancel:bundles|back:bundles)")
            ],
            BUNDLES_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & not_keyboard_button, bundles_phone),
                CallbackQueryHandler(bundles_phone, pattern="^(back:bundles|cancel:bundles)")
            ],
        },
        fallbacks=[
            CommandHandler("cancel", bundles_cancel),
            # Allow keyboard buttons to exit conversation and route to appropriate handler
            MessageHandler(keyboard_button_filter, handle_keyboard_button_exit),
        ],
        per_message=False
    )
    application.add_handler(bundles_conv)
    
    # Message handlers for main keyboard buttons
    # Add these AFTER conversation handlers so they handle the buttons when conversation exits
    application.add_handler(MessageHandler(filters.Regex("^💼 Balance$"), balance_handler))
    application.add_handler(MessageHandler(filters.Regex("^📜 History$"), history_handler))
    application.add_handler(MessageHandler(filters.Regex("^🎯 Referral$"), referral_command))
    application.add_handler(MessageHandler(filters.Regex("^❓ Help$"), help_handler))


async def main():
    """Main function to run the bot."""
    # Create application
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    # Set up handlers
    setup_handlers(application)
    
    # Start the bot
    logger.info("Starting bot...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    logger.info("Bot is running. Press Ctrl+C to stop.")
    
    # Keep the bot running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

