import logging
from typing import Optional, List, Dict, Any
from uuid import uuid4
from decimal import Decimal
from datetime import datetime
from app.repository.base import BaseRepository
from app.core.constants import OrderStatus

logger = logging.getLogger(__name__)


class OrderRepository(BaseRepository):
    """Repository for order operations."""
    
    def __init__(self):
        super().__init__("orders")
    
    async def get_by_user_id(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get orders by user ID, ordered by created_at descending.
        
        Args:
            user_id: The user ID
            limit: Maximum number of orders to return
            
        Returns:
            List of order records
        """
        try:
            response = await (
                self.client.table(self.table_name)
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching orders for user {user_id}: {str(e)}")
            return []
    
    async def create_order(
        self,
        user_id: str,
        bundle_id: str,
        phone: str,
        price: Decimal,
        status: str = "pending",
        delivery_status: str = "pending",
        vendor_reference: Optional[str] = None,
        vendor_response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new order.
        
        Args:
            user_id: The user ID
            bundle_id: The bundle ID being purchased
            phone: Phone number to receive the bundle
            price: Order price
            status: Order status (default: "pending")
            delivery_status: Delivery status (default: "pending")
            vendor_reference: Optional vendor reference number
            vendor_response: Optional raw response from vendor
            
        Returns:
            The created order record
            
        Raises:
            ValueError: If order creation fails
        """
        order_data = {
            "id": str(uuid4()),
            "user_id": user_id,
            "bundle_id": bundle_id,
            "phone": phone,
            "price": str(price),
            "status": status,
            "delivery_status": delivery_status,
            "vendor_reference": vendor_reference,
            "vendor_response": vendor_response,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        try:
            order = await self.create(order_data)
            logger.info(f"Created order {order['id']} for user {user_id}")
            return order
        except Exception as e:
            logger.error(f"Error creating order for user {user_id}: {str(e)}")
            raise
    
    async def update_order_status(
        self,
        order_id: str,
        status: str,
        delivery_status: Optional[str] = None,
        vendor_reference: Optional[str] = None,
        vendor_response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update order status.
        
        Args:
            order_id: The order ID
            status: New status
            delivery_status: Optional new delivery status
            vendor_reference: Optional vendor reference number
            vendor_response: Optional updated vendor response
            
        Returns:
            The updated order record
            
        Raises:
            ValueError: If update fails
        """
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        if delivery_status:
            update_data["delivery_status"] = delivery_status
        if vendor_reference:
            update_data["vendor_reference"] = vendor_reference
        if vendor_response:
            update_data["vendor_response"] = vendor_response
        
        try:
            order = await self.update(order_id, update_data)
            logger.info(f"Updated order {order_id} status to {status}")
            return order
        except Exception as e:
            logger.error(f"Error updating order {order_id}: {str(e)}")
            raise
    
    async def get_by_vendor_reference(self, vendor_reference: str) -> Optional[Dict[str, Any]]:
        """
        Get order by vendor reference.
        
        Args:
            vendor_reference: The vendor reference number
            
        Returns:
            Order record if found, None otherwise
        """
        return await self.get_by_field("vendor_reference", vendor_reference)
    
    async def get_pending_orders(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all pending orders.
        
        Args:
            limit: Maximum number of orders to return
            
        Returns:
            List of pending order records
        """
        try:
            response = await (
                self.client.table(self.table_name)
                .select("*")
                .eq("status", "pending")
                .order("created_at", desc=False)  # Oldest first
                .limit(limit)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching pending orders: {str(e)}")
            return []
    
    async def get_orders_by_status(
        self, 
        status: str, 
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get orders by status, optionally filtered by user.
        
        Args:
            status: Order status to filter by
            user_id: Optional user ID to filter by
            limit: Maximum number of orders to return
            
        Returns:
            List of order records
        """
        try:
            query = (
                self.client.table(self.table_name)
                .select("*")
                .eq("status", status)
            )
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            query = query.order("created_at", desc=True).limit(limit)
            response = await query.execute()
            
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching orders by status {status}: {str(e)}")
            return []
    
    async def get_completed_orders(
        self, 
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get completed orders, optionally filtered by user.
        
        Args:
            user_id: Optional user ID to filter by
            limit: Maximum number of orders to return
            
        Returns:
            List of completed order records
        """
        return await self.get_orders_by_status("completed", user_id, limit)
    
    async def get_failed_orders(
        self, 
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get failed orders, optionally filtered by user.
        
        Args:
            user_id: Optional user ID to filter by
            limit: Maximum number of orders to return
            
        Returns:
            List of failed order records
        """
        return await self.get_orders_by_status("failed", user_id, limit)
    
    async def get_orders_with_bundles(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get orders with bundle information joined.
        
        Args:
            user_id: The user ID
            limit: Maximum number of orders to return
            
        Returns:
            List of order records with bundle data
        """
        try:
            # Using Supabase's foreign key relationship to join bundles
            response = await (
                self.client.table(self.table_name)
                .select("*, bundles(*)")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            logger.warning(f"Error fetching orders with bundles: {str(e)}")
            # Fallback to regular orders if join fails
            return await self.get_by_user_id(user_id, limit)
    
    async def get_user_order_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get order summary statistics for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            Dictionary with order statistics
        """
        try:
            all_orders = await self.get_by_user_id(user_id, limit=1000)
            
            total_spent = sum(
                Decimal(o["price"]) 
                for o in all_orders 
                if o["status"] == OrderStatus.SUCCESS.value
            )
            
            completed_count = sum(
                1 for o in all_orders if o["status"] == OrderStatus.SUCCESS.value
            )
            
            pending_count = sum(
                1 for o in all_orders if o["status"] == OrderStatus.PENDING.value
            )
            
            failed_count = sum(
                1 for o in all_orders if o["status"] == OrderStatus.FAILED.value
            )
            
            return {
                "total_orders": len(all_orders),
                "completed_orders": completed_count,
                "pending_orders": pending_count,
                "failed_orders": failed_count,
                "total_spent": str(total_spent)
            }
        except Exception as e:
            logger.error(f"Error getting order summary for user {user_id}: {str(e)}")
            return {
                "total_orders": 0,
                "completed_orders": 0,
                "pending_orders": 0,
                "failed_orders": 0,
                "total_spent": "0"
            }
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order (only if still pending).
        
        Args:
            order_id: The order ID
            
        Returns:
            The updated order record
            
        Raises:
            ValueError: If order cannot be cancelled
        """
        order = await self.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order["status"] != "pending":
            raise ValueError(f"Cannot cancel order with status: {order['status']}")
        
        return await self.update_order_status(order_id, "cancelled")