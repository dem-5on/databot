import asyncio
import logging
from telegram import Bot
from app.core.config import settings
from app.celery_app import celery_app
from app.services.whatsapp_notifier import WhatsAppNotifierService
from app.repository.telegram_user_repo import TelegramUserRepository
from app.repository.whatsapp_user_repo import WhatsAppUserRepository
    
logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in sync Celery context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="app.tasks.sync_bundles_task")
def sync_bundles_task(self):
    """
    Celery task for bundle sync (DEPRECATED for Blessdatahub).
    
    Blessdatahub uses static pricing. Bundles are seeded via SQL script.
    This task now skips the sync and returns a warning.
    """
    logger.info("⚠️ Bundle sync task called - skipping (Blessdatahub uses static pricing)")
    return {
        "status": "skipped", 
        "message": "Blessdatahub uses static bundle prices. Use seed_bundles.sql to populate bundles."
    }


@celery_app.task(bind=True, name="app.tasks.broadcast_telegram")
def broadcast_telegram(self, message: str, user_ids: list = None, batch_size: int = 20, interval_seconds: int = 300):
    """
    Send broadcast message to Telegram users.
    
    Args:
        message: Message text to send
        user_ids: Optional list of telegram_ids. If None, sends to all users.
        batch_size: Number of users per batch
        interval_seconds: Seconds to wait between batches
    """
    
    async def _broadcast():
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        telegram_repo = TelegramUserRepository()
        
        # Get users
        if user_ids:
            users = [{"telegram_id": tid} for tid in user_ids]
        else:
            users = await telegram_repo.get_all(limit=10000)
        
        total = len(users)
        sent = 0
        failed = 0
        errors = []
        
        logger.info(f"Starting Telegram broadcast to {total} users (batch={batch_size}, interval={interval_seconds}s)")
        
        for i in range(0, total, batch_size):
            batch = users[i:i + batch_size]
            
            for user in batch:
                telegram_id = user.get("telegram_id")
                if not telegram_id:
                    continue
                    
                try:
                    await bot.send_message(chat_id=telegram_id, text=message)
                    sent += 1
                    logger.debug(f"Sent to Telegram user {telegram_id}")
                except Exception as e:
                    failed += 1
                    error_msg = str(e)[:100]
                    errors.append({"telegram_id": telegram_id, "error": error_msg})
                    logger.warning(f"Failed to send to {telegram_id}: {error_msg}")
            
            # Wait between batches (except for last batch)
            if i + batch_size < total:
                logger.info(f"Telegram broadcast: sent {sent}/{total}, waiting {interval_seconds}s before next batch...")
                await asyncio.sleep(interval_seconds)
        
        await bot.close()
        logger.info(f"Telegram broadcast complete: sent={sent}, failed={failed}")
        return {"sent": sent, "failed": failed, "total": total, "errors": errors[:10]}
    
    return run_async(_broadcast())


@celery_app.task(bind=True, name="app.tasks.broadcast_whatsapp")
def broadcast_whatsapp(self, message: str, user_ids: list = None, batch_size: int = 20, interval_seconds: int = 300):
    """
    Send broadcast message to WhatsApp users.
    
    Args:
        message: Message text to send
        user_ids: Optional list of phone numbers. If None, sends to all users.
        batch_size: Number of users per batch
        interval_seconds: Seconds to wait between batches
    """
    
    async def _broadcast():
        notifier = WhatsAppNotifierService()
        whatsapp_repo = WhatsAppUserRepository()
        
        # Get users
        if user_ids:
            users = [{"phone": pid} for pid in user_ids]
        else:
            users = await whatsapp_repo.get_all(limit=10000)
        
        total = len(users)
        sent = 0
        failed = 0
        errors = []
        
        logger.info(f"Starting WhatsApp broadcast to {total} users (batch={batch_size}, interval={interval_seconds}s)")
        
        for i in range(0, total, batch_size):
            batch = users[i:i + batch_size]
            
            for user in batch:
                phone = user.get("phone")
                if not phone:
                    continue
                    
                try:
                    success = await notifier.send_text_message(phone, message)
                    if success:
                        sent += 1
                        logger.debug(f"Sent to WhatsApp user {phone}")
                    else:
                        failed += 1
                        errors.append({"phone": phone, "error": "send_text_message returned False"})
                except Exception as e:
                    failed += 1
                    error_msg = str(e)[:100]
                    errors.append({"phone": phone, "error": error_msg})
                    logger.warning(f"Failed to send to {phone}: {error_msg}")
            
            # Wait between batches (except for last batch)
            if i + batch_size < total:
                logger.info(f"WhatsApp broadcast: sent {sent}/{total}, waiting {interval_seconds}s before next batch...")
                await asyncio.sleep(interval_seconds)
        
        logger.info(f"WhatsApp broadcast complete: sent={sent}, failed={failed}")
        return {"sent": sent, "failed": failed, "total": total, "errors": errors[:10]}
    
    return run_async(_broadcast())
