import asyncio
import logging
from app.utils.health_checks import check_all_services
from app.repository.health_repo import HealthLogRepository

logger = logging.getLogger(__name__)

async def monitor_health_task():
    """Foundational task to monitor system health periodically."""
    repo = HealthLogRepository()
    logger.info("Starting health monitoring task")
    
    while True:
        try:
            results = await check_all_services()
            
            for result in results:
                await repo.log_health(
                    service_name=result["name"],
                    status=result["status"],
                    latency_ms=result["latency"]
                )
                
            # Log summary
            logger.info(f"Health check completed for {len(results)} services")
            
        except Exception as e:
            logger.error(f"Error in health monitoring task: {e}")
            
        # Wait for 60 seconds before next check
        # In production, this might be configurable or handled by Celery Beat
        await asyncio.sleep(60)
