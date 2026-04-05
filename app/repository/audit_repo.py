import logging
from uuid import uuid4
from datetime import datetime
from typing import Optional, Dict, Any
from app.repository.base import BaseRepository

logger = logging.getLogger(__name__)


class AuditLogRepository(BaseRepository):
    """Repository for system audit logs."""
    
    def __init__(self):
        super().__init__("audit_logs")
    
    async def log_action(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Log an admin or system action.
        
        Args:
            user_id: ID of user performing action
            action: Action name (e.g., "create", "update", "delete")
            resource_type: Type of resource (e.g., "bundle", "user")
            resource_id: ID of the resource
            details: Additional details/payload
            ip_address: IP address of request
            user_agent: User agent string
            
        Returns:
            Created log entry
        """
        log_entry = {
            "id": str(uuid4()),
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            return await self.create(log_entry)
        except Exception as e:
            # Fallback for logging if DB fails
            logger.error(f"Failed to write audit log to DB: {e}")
            logger.info(f"AUDIT LOG: {log_entry}")
            return log_entry

    async def get_logs(
        self, 
        limit: int = 50, 
        offset: int = 0,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get filtered audit logs."""
        query = self.client.table(self.table_name).select("*")
        
        if user_id:
            query = query.eq("user_id", user_id)
        if action:
            query = query.eq("action", action)
        if resource_type:
            query = query.eq("resource_type", resource_type)
            
        # Get count
        # (Supabase client might behave differently for count, skipping complex count for now)
        
        # Get data
        response = await query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        return response.data if response.data else []
