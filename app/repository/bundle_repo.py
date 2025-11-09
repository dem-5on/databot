from typing import Optional, List, Dict, Any
from uuid import uuid4
from decimal import Decimal
from app.repository.base import BaseRepository


class BundleRepository(BaseRepository):
    """Repository for bundle operations."""
    
    def __init__(self):
        super().__init__("bundles")
    
    def get_by_network(self, network: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get bundles by network."""
        query = self.client.table(self.table_name).select("*").eq("network", network)
        if active_only:
            query = query.eq("active", True)
        response = query.execute()
        return response.data if response.data else []
    
    def get_active_bundles(self, network: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active bundles, optionally filtered by network."""
        query = self.client.table(self.table_name).select("*").eq("active", True)
        if network:
            query = query.eq("network", network)
        response = query.order("price", desc=False).execute()
        return response.data if response.data else []
    
    def upsert_bundle(
        self,
        network: str,
        capacity: str,
        mb: str,
        price: Decimal,
        currency: str = "GHS",
        active: bool = True
    ) -> Dict[str, Any]:
        """Upsert a bundle (insert or update based on network + capacity)."""
        # First, try to find existing bundle with same network and capacity
        existing = (
            self.client.table(self.table_name)
            .select("*")
            .eq("network", network)
            .eq("capacity", capacity)
            .execute()
        )
        
        bundle_data = {
            "network": network,
            "capacity": capacity,
            "mb": mb,
            "price": str(price),
            "currency": currency,
            "active": active
        }
        
        if existing.data:
            # Update existing bundle
            bundle_id = existing.data[0]["id"]
            return self.update(bundle_id, bundle_data)
        else:
            # Create new bundle
            bundle_data["id"] = str(uuid4())
            return self.create(bundle_data)
    
    def get_by_id(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        """Get bundle by ID."""
        return super().get_by_id(bundle_id)

