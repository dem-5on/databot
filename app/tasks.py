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
    Celery task for bundle sync (DEPRECATED for Blessdatahub).
    
    Blessdatahub uses static pricing. Bundles are seeded via SQL script.
    This task now skips the sync and returns a warning.
    """
    logger.info("⚠️ Bundle sync task called - skipping (Blessdatahub uses static pricing)")
    return {
        "status": "skipped", 
        "message": "Blessdatahub uses static bundle prices. Use seed_bundles.sql to populate bundles."
    }
