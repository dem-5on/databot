import logging
from uuid import uuid4
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.repository.base import BaseRepository

logger = logging.getLogger(__name__)


class TransactionRepository(BaseRepository):
    """Repository for transaction operations."""
    
    def __init__(self):
        super().__init__("transactions")
    
    async def get_by_reference(self, reference: str) -> Optional[Dict[str, Any]]:
        """
        Get transaction by reference.
        
        Args:
            reference: The transaction reference
            
        Returns:
            Transaction record if found, None otherwise
        """
        return await self.get_by_field("reference", reference)
    
    async def get_by_user_id(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get transactions by user ID, ordered by created_at descending.
        
        Args:
            user_id: The user ID
            limit: Maximum number of transactions to return
            
        Returns:
            List of transaction records
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
            logger.error(f"Error fetching transactions for user {user_id}: {str(e)}")
            return []
    
    async def create_transaction(
        self,
        user_id: str,
        transaction_type: str,
        amount: Decimal,
        currency: str,
        reference: str,
        status: str = "pending",
        phone: Optional[str] = None,
        provider: Optional[str] = None,
        raw_payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new transaction.
        
        Args:
            user_id: The user ID
            transaction_type: Type of transaction (e.g., "deposit", "withdrawal", "purchase")
            amount: Transaction amount
            currency: Currency code (e.g., "GHS")
            reference: Unique transaction reference
            status: Transaction status (default: "pending")
            phone: Optional phone number
            provider: Optional payment provider
            raw_payload: Optional raw response data from provider
            
        Returns:
            The created transaction record
            
        Raises:
            ValueError: If transaction creation fails
        """
        transaction_data = {
            "id": str(uuid4()),
            "user_id": user_id,
            "type": transaction_type,
            "amount": str(amount),
            "currency": currency,
            "reference": reference,
            "status": status,
            "phone": phone,
            "provider": provider,
            "raw_payload": raw_payload,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        try:
            transaction = await self.create(transaction_data)
            logger.info(f"Created transaction {reference} for user {user_id}")
            return transaction
        except Exception as e:
            logger.error(f"Error creating transaction {reference}: {str(e)}")
            raise
    
    async def update_transaction_status(
        self,
        transaction_id: str,
        status: str,
        raw_payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update transaction status.
        
        Args:
            transaction_id: The transaction ID
            status: New status
            raw_payload: Optional updated raw response data
            
        Returns:
            The updated transaction record
            
        Raises:
            ValueError: If update fails
        """
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        if raw_payload:
            update_data["raw_payload"] = raw_payload
        
        try:
            transaction = await self.update(transaction_id, update_data)
            logger.info(f"Updated transaction {transaction_id} status to {status}")
            return transaction
        except Exception as e:
            logger.error(f"Error updating transaction {transaction_id}: {str(e)}")
            raise
    
    async def update_transaction_by_reference(
        self,
        reference: str,
        status: str,
        raw_payload: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update transaction by reference.
        
        Args:
            reference: The transaction reference
            status: New status
            raw_payload: Optional updated raw response data
            
        Returns:
            The updated transaction record, or None if not found
        """
        transaction = await self.get_by_reference(reference)
        if not transaction:
            logger.warning(f"Transaction not found with reference {reference}")
            return None
        
        return await self.update_transaction_status(
            transaction["id"], 
            status, 
            raw_payload
        )
    
    async def get_by_paystack_reference(self, paystack_ref: str) -> Optional[Dict[str, Any]]:
        """
        Get transaction by Paystack reference (efficient database query).
        
        This uses PostgreSQL's JSON operators to search within the raw_payload field.
        Much more efficient than loading all records into memory.
        
        Args:
            paystack_ref: The Paystack reference to search for
            
        Returns:
            Transaction record if found, None otherwise
        """
        try:
            # Use PostgreSQL JSON operators to query raw_payload
            # This queries: raw_payload->'data'->>'reference' = paystack_ref
            response = await (
                self.client.table(self.table_name)
                .select("*")
                .eq("raw_payload->data->>reference", paystack_ref)
                .limit(1)
                .execute()
            )
            
            if response.data and len(response.data) > 0:
                logger.info(f"Found transaction with Paystack reference {paystack_ref}")
                return response.data[0]
            
            logger.info(f"No transaction found with Paystack reference {paystack_ref}")
            return None
            
        except Exception as e:
            logger.error(f"Error querying Paystack reference {paystack_ref}: {str(e)}")
            # Fallback to the old method if JSON query fails
            logger.warning("Falling back to in-memory search method")
            return await self._get_by_paystack_reference_fallback(paystack_ref)
    
    async def _get_by_paystack_reference_fallback(self, paystack_ref: str) -> Optional[Dict[str, Any]]:
        """
        Fallback method for searching Paystack reference (less efficient).
        
        This loads recent transactions into memory and searches through them.
        Should only be used if the JSON query method fails.
        """
        try:
            response = await (
                self.client.table(self.table_name)
                .select("*")
                .order("created_at", desc=True)
                .limit(1000)  # Get recent transactions
                .execute()
            )
            
            if not response.data:
                return None
            
            # Search through transactions for matching Paystack reference
            for transaction in response.data:
                raw_payload = transaction.get("raw_payload")
                if isinstance(raw_payload, dict):
                    payload_ref = raw_payload.get("data", {}).get("reference")
                    if payload_ref == paystack_ref:
                        logger.info(f"Found transaction with Paystack reference {paystack_ref} (fallback)")
                        return transaction
            
            return None
            
        except Exception as e:
            logger.error(f"Error in fallback Paystack reference search: {str(e)}")
            return None
    
    async def get_pending_transactions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all pending transactions.
        
        Args:
            limit: Maximum number of transactions to return
            
        Returns:
            List of pending transaction records
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
            logger.error(f"Error fetching pending transactions: {str(e)}")
            return []
    
    async def get_transactions_by_status(
        self, 
        status: str, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get transactions by status.
        
        Args:
            status: Transaction status to filter by
            limit: Maximum number of transactions to return
            
        Returns:
            List of transaction records
        """
        return await self.get_all_by_field("status", status, limit=limit)
    
    async def get_transactions_by_type(
        self, 
        transaction_type: str, 
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get transactions by type, optionally filtered by user.
        
        Args:
            transaction_type: Type of transaction to filter by
            user_id: Optional user ID to filter by
            limit: Maximum number of transactions to return
            
        Returns:
            List of transaction records
        """
        try:
            query = (
                self.client.table(self.table_name)
                .select("*")
                .eq("type", transaction_type)
            )
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            query = query.order("created_at", desc=True).limit(limit)
            response = await query.execute()
            
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching transactions by type {transaction_type}: {str(e)}")
            return []
    
    async def get_user_transaction_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get transaction summary for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            Dictionary with transaction statistics
        """
        try:
            all_transactions = await self.get_by_user_id(user_id, limit=1000)
            
            total_deposits = sum(
                Decimal(t["amount"]) 
                for t in all_transactions 
                if t["type"] == "deposit" and t["status"] == "completed"
            )
            
            total_purchases = sum(
                Decimal(t["amount"]) 
                for t in all_transactions 
                if t["type"] == "purchase" and t["status"] == "completed"
            )
            
            pending_count = sum(
                1 for t in all_transactions if t["status"] == "pending"
            )
            
            return {
                "total_transactions": len(all_transactions),
                "total_deposits": str(total_deposits),
                "total_purchases": str(total_purchases),
                "pending_count": pending_count
            }
        except Exception as e:
            logger.error(f"Error getting transaction summary for user {user_id}: {str(e)}")
            return {
                "total_transactions": 0,
                "total_deposits": "0",
                "total_purchases": "0",
                "pending_count": 0
            }