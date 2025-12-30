from fastapi import APIRouter
from app.repository.base import BaseRepository
import time
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("")
async def health_check():
    """
    System health check endpoint.
    Checks database connection and reports system status.
    """
    start_time = time.time()
    db_status = "unknown"
    db_latency = 0
    
    try:
        # Check simple DB query using BaseRepository
        repo = BaseRepository("base_users")
        db_start = time.time()
        # Just check if we can query, explicit count might be slow so just limit 1
        await repo.get_all(limit=1) 
        db_latency = (time.time() - db_start) * 1000
        db_status = "connected"
    except Exception as e:
        logger.error(f"Health check DB failure: {e}")
        db_status = "disconnected"
        
    uptime = time.time() - start_time
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": time.time(),
        "components": {
            "database": {
                "status": db_status,
                "latency_ms": round(db_latency, 2)
            },
            "api": {
                "status": "online",
                "uptime": round(uptime, 4)
            }
        },
        "version": "1.0.0"
    }
