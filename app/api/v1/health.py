from fastapi import APIRouter
import time
import logging
from app.utils.health_checks import check_all_services
from app.repository.health_repo import HealthLogRepository
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("")
async def health_check():
    """
    System health check endpoint.
    Checks database connection and reports system status.
    """
    start_time = time.time()
    repo = HealthLogRepository()
    
    # Get current status (real-time)
    current_status = await check_all_services()
    
    # Enhance with historical uptime
    services_status = []
    
    # We can fetch uptimes in parallel
    async def attach_uptime(service):
        try:
            uptime = await repo.get_uptime_percentage(service["name"])
        except Exception:
            uptime = 0.0
        
        # If uptime is 0 (no logs yet), default to perfect if currently healthy (optimistic) 
        # or stick to 0? User asked for option 3, so meaningful data. 
        # If no logs, let's show what we have (0 or 100 based on current?). 
        # Let's show 100 if current is healthy and no history to avoid scaring users, 
        # or maybe 0 implies "no data". 
        # Actually, let's trust the repo result. If 0 logs, repo returns 0.
        
        return {
            **service,
            "uptime": uptime,
            "lastCheck": "Just now"
        }

    services_status = await asyncio.gather(*[attach_uptime(s) for s in current_status])

    # Calculate overall health
    all_healthy = all(s["status"] == "operational" for s in services_status)
    api_uptime = time.time() - start_time

    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": time.time(),
        "services": services_status,
        "version": "1.0.0"
    }


@router.get("/logs")
async def get_health_logs(limit: int = 20):
    """
    Get recent health check logs.
    """
    repo = HealthLogRepository()
    try:
        logs = await repo.get_all(limit=limit, order_by="created_at", ascending=False)
        
        # Map status to log level for display
        formatted_logs = []
        for log in logs:
            level = "info"
            if log.get("status") == "down":
                level = "error"
            elif log.get("status") == "degraded":
                level = "warning"
            
            formatted_logs.append({
                "id": str(log.get("id")),
                "level": level,
                "message": f"{log.get('service_name')} - {log.get('status')} ({log.get('latency_ms', 0)}ms)",
                "timestamp": log.get("created_at", ""),
                "service": log.get("service_name", "Unknown")
            })
        
        return {"logs": formatted_logs}
    except Exception as e:
        logger.error(f"Error fetching health logs: {e}")
        return {"logs": []}
