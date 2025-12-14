"""Celery tasks for background processing."""
import asyncio
import logging
from app.celery_app import celery_app
from app.services.bundle_sync import BundleSyncService

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
    Celery task to sync bundles from DatamartGH.
    
    This runs as a scheduled task via Celery Beat (daily at midnight)
    or can be triggered manually.
    """
    logger.info("🔄 Starting Celery bundle sync task...")
    
    sync_service = BundleSyncService()
    try:
        count = run_async(sync_service.sync_bundles_to_db())
        logger.info(f"✅ Celery sync completed: {count} bundles synced")
        return {"status": "success", "bundles_synced": count}
    except Exception as e:
        logger.error(f"❌ Celery sync failed: {str(e)}")
        # Retry on failure (max 3 retries with exponential backoff)
        raise self.retry(exc=e, countdown=60, max_retries=3)
