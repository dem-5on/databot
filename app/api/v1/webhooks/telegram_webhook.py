import logging
from telegram import Update
from app.core.config import settings
from fastapi import APIRouter, Request, HTTPException, Header

logger = logging.getLogger(__name__)

router = APIRouter()

# Bot application instance - set by main.py during startup
_bot_application = None


def set_bot_application(app):
    """Set the bot application instance for processing updates."""
    global _bot_application
    _bot_application = app
    logger.info("Bot application set for webhook processing")


def get_bot_application():
    """Get the bot application instance."""
    return _bot_application


@router.post("")
async def handle_telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None, alias="X-Telegram-Bot-Api-Secret-Token")
):
    """
    Handle incoming Telegram webhook updates.
    
    Telegram sends updates to this endpoint when using webhook mode.
    The secret token header is validated for security.
    """
    # Validate secret token if configured
    if settings.TELEGRAM_WEBHOOK_SECRET:
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
            logger.warning("Invalid Telegram webhook secret token")
            raise HTTPException(status_code=403, detail="Invalid secret token")
    
    # Ensure bot application is initialized
    if _bot_application is None:
        logger.error("Bot application not initialized")
        raise HTTPException(status_code=500, detail="Bot not initialized")
    
    try:
        # Parse the update JSON
        update_data = await request.json()
        
        # Create Update object from the received data
        update = Update.de_json(update_data, _bot_application.bot)
        
        # Process the update through bot handlers
        await _bot_application.process_update(update)
        
        logger.debug(f"Processed Telegram update: {update.update_id}")
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}", exc_info=True)
        # Return 200 to prevent Telegram from retrying
        # Log the error and investigate, but don't block Telegram
        return {"status": "error", "message": str(e)}
