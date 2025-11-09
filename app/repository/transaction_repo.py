from typing import Optional, List, Dict, Any
from uuid import uuid4
from decimal import Decimal
from datetime import datetime
from app.repository.base import BaseRepository


class TransactionRepository(BaseRepository):
    """Repository for transaction operations."""
    
    def __init__(self):
        super().__init__("transactions")
    
    def get_by_reference(self, reference: str) -> Optional[Dict[str, Any]]:
        """Get transaction by reference."""
        return self.get_by_field("reference", reference)
    
    def get_by_user_id(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get transactions by user ID, ordered by created_at descending."""
        response = (
            self.client.table(self.table_name)
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data if response.data else []
    
    def create_transaction(
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
        """Create a new transaction."""
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
        return self.create(transaction_data)
    
    def update_transaction_status(
        self,
        transaction_id: str,
        status: str,
        raw_payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update transaction status."""
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        if raw_payload:
            update_data["raw_payload"] = raw_payload
        return self.update(transaction_id, update_data)
    
    def update_transaction_by_reference(
        self,
        reference: str,
        status: str,
        raw_payload: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Update transaction by reference."""
        transaction = self.get_by_reference(reference)
        if not transaction:
            return None
        return self.update_transaction_status(transaction["id"], status, raw_payload)
    
    def get_by_paystack_reference(self, paystack_ref: str) -> Optional[Dict[str, Any]]:
        """
        Get transaction by Paystack reference.
        Searches in raw_payload->data->reference JSON field.
        """
        # Supabase/PostgREST supports JSON querying, but it's limited
        # We'll search through recent transactions and check raw_payload
        # For better performance, consider adding a paystack_reference column
        response = (
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
                    return transaction
        
        return None

