from typing import Optional, List, Dict, Any
from uuid import uuid4
from decimal import Decimal
from datetime import datetime
from app.repository.base import BaseRepository


class OrderRepository(BaseRepository):
    """Repository for order operations."""
    
    def __init__(self):
        super().__init__("orders")
    
    def get_by_user_id(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get orders by user ID, ordered by created_at descending."""
        response = (
            self.client.table(self.table_name)
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data if response.data else []
    
    def create_order(
        self,
        user_id: str,
        bundle_id: str,
        phone: str,
        price: Decimal,
        status: str = "pending",
        vendor_reference: Optional[str] = None,
        vendor_response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new order."""
        order_data = {
            "id": str(uuid4()),
            "user_id": user_id,
            "bundle_id": bundle_id,
            "phone": phone,
            "price": str(price),
            "status": status,
            "vendor_reference": vendor_reference,
            "vendor_response": vendor_response,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        return self.create(order_data)
    
    def update_order_status(
        self,
        order_id: str,
        status: str,
        vendor_reference: Optional[str] = None,
        vendor_response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update order status."""
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        if vendor_reference:
            update_data["vendor_reference"] = vendor_reference
        if vendor_response:
            update_data["vendor_response"] = vendor_response
        return self.update(order_id, update_data)

