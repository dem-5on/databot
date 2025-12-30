import logging
import secrets
import string
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import uuid4
from app.repository.base import BaseRepository

logger = logging.getLogger(__name__)


class AdminTokenRepository(BaseRepository):
    """Repository for managing admin access tokens."""
    
    def __init__(self):
        super().__init__("admin_tokens")
    
    @staticmethod
    def generate_token(length: int = 64) -> str:
        """Generate a secure random token."""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    async def create_token(self, name: str, created_by: str) -> Dict[str, Any]:
        """Create a new admin token."""
        token = self.generate_token()
        
        data = {
            "id": str(uuid4()),
            "name": name,
            "token": token,
            "created_by": created_by,
            "created_at": datetime.utcnow().isoformat(),
            "active": True,
            "last_used_at": None
        }
        
        try:
            return await self.create(data)
        except Exception as e:
            logger.error(f"Error creating admin token: {e}")
            raise
            
    async def get_active_tokens(self) -> List[Dict[str, Any]]:
        """Get all active tokens."""
        try:
            response = await (
                self.client.table(self.table_name)
                .select("*")
                .eq("active", True)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching active tokens: {e}")
            return []
            
    async def revoke_token(self, token_id: str) -> bool:
        """Revoke (deactivate) a token."""
        try:
            await self.update(token_id, {"active": False})
            return True
        except Exception as e:
            logger.error(f"Error revoking token {token_id}: {e}")
            return False
            
    async def validate_token(self, token: str) -> bool:
        """Validate if a token exists and is active."""
        try:
            record = await self.get_by_field("token", token)
            if record and record.get("active"):
                # Update last used async (don't await strictly to fast return)
                # In prod, fire and forget or background task
                await self.update(record["id"], {
                    "last_used_at": datetime.utcnow().isoformat()
                })
                return True
            return False
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False
