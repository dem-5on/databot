import time
import logging
from fastapi import APIRouter
from app.utils.health_checks import check_all_services
from app.repository.health_repo import HealthLogRepository

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
    
    for service in current_status:
        try:
            uptime = await repo.get_uptime_percentage(service["name"])
        except Exception:
            uptime = 0.0
        
        services_status.append({
            **service,
            "uptime": uptime,
            "lastCheck": "Just now"
        })

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
