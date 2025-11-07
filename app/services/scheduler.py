from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.db.session import AsyncSessionLocal
from app.services.bundle_sync import BundleSyncService
import logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def sync_bundles_job():
    """Background job to sync bundles from DatamartGH."""
    logger.info("Starting scheduled bundle sync...")
    
    async with AsyncSessionLocal() as db:
        sync_service = BundleSyncService()
        try:
            count = await sync_service.sync_bundles_to_db(db)
            logger.info(f"✅ Scheduled sync completed: {count} bundles synced")
        except Exception as e:
            logger.error(f"❌ Scheduled sync failed: {str(e)}")


def start_scheduler():
    """Start the scheduler with all jobs."""
    
    # Sync bundles every 24 hours at 2 AM
    scheduler.add_job(
        sync_bundles_job,
        trigger=CronTrigger(hour=2, minute=0),  # Runs at 2:00 AM daily
        id="sync_bundles_daily",
        name="Sync bundles from DatamartGH",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("📅 Scheduler started - Bundle sync will run daily at 2:00 AM")


def stop_scheduler():
    """Stop the scheduler."""
    scheduler.shutdown()
    logger.info("📅 Scheduler stopped")