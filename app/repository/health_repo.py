from app.repository.base import BaseRepository
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class HealthLogRepository(BaseRepository):
    def __init__(self):
        super().__init__("health_logs")

    async def log_health(self, service_name: str, status: str, latency_ms: int):
        """Log a health check result."""
        data = {
            "service_name": service_name,
            "status": status,
            "latency_ms": latency_ms
        }
        await self.create(data)

    async def get_uptime_percentage(self, service_name: str, days: int = 30) -> float:
        """Calculate uptime percentage for the last N days."""
        try:
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            # Since Supabase-py doesn't support complex aggregation easily via simple client,
            # we will fetch relevant logs. 
            # Note: For production with many logs, this should be an RPC call or optimized.
            # For now, we'll limit to last 1000 logs to estimate or use an RPC if we had one.
            # Let's try to filter by date and get count.
            
            query = self.client.table(self.table_name).select("status", count="exact")\
                .eq("service_name", service_name)\
                .gte("created_at", start_date)
            
            result = await query.execute()
            total_checks = result.count
            
            if total_checks == 0:
                return 0.0
                
            # Count healthy
            query_healthy = self.client.table(self.table_name).select("status", count="exact")\
                .eq("service_name", service_name)\
                .gte("created_at", start_date)\
                .eq("status", "operational")
                
            result_healthy = await query_healthy.execute()
            healthy_checks = result_healthy.count
            
            return round((healthy_checks / total_checks) * 100, 2)
            
        except Exception as e:
            logger.error(f"Error calculating uptime for {service_name}: {e}")
            return 0.0
