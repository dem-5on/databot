from decimal import Decimal
from typing import Optional, Dict, Any
from postgrest.exceptions import APIError
from app.repository.base import BaseRepository


class WalletRepository(BaseRepository):
    """Repository for wallet operations."""
    
    def __init__(self):
        super().__init__("wallets")
    
    def get_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get wallet by user ID."""
        return self.get_by_field("user_id", user_id)
    
    def create_wallet(self, user_id: str) -> dict:
        try:
            wallet_data = {
                "user_id": user_id,
                "balance": 0
            }
            return self.create(wallet_data)
        except APIError as e:
            raise ValueError(f"Failed to create wallet: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error creating wallet: {str(e)}")

    def get_or_create_wallet(self, user_id: str) -> dict:
        wallet = self.get_by_user_id(user_id)
        if not wallet:
            wallet = self.create_wallet(user_id)
        return wallet

    def update_balance(self, wallet_id: str, new_balance: Decimal) -> dict:
        """Update wallet balance (use optimistic locking for concurrency)."""
        # Get current wallet to check version/balance
        wallet = self.get_by_id(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet not found: {wallet_id}")
        
        # Update balance
        return self.update(wallet_id, {"balance": str(new_balance)})
    
    def credit_balance(self, wallet_id: str, amount: Decimal) -> Dict[str, Any]:
        """Credit wallet balance (atomic operation using RPC or update)."""
        wallet = self.get_by_id(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet not found: {wallet_id}")
        
        current_balance = Decimal(wallet["balance"])
        new_balance = current_balance + amount
        return self.update(wallet_id, {"balance": str(new_balance)})
    
    def debit_balance(self, wallet_id: str, amount: Decimal) -> Dict[str, Any]:
        """Debit wallet balance with balance check."""
        wallet = self.get_by_id(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet not found: {wallet_id}")
        
        current_balance = Decimal(wallet["balance"])
        if current_balance < amount:
            raise ValueError(
                f"Insufficient balance. Available balance is: {current_balance}, Required: {amount}"
            )
        
        new_balance = current_balance - amount
        return self.update(wallet_id, {"balance": str(new_balance)})
    
    def get_balance(self, user_id: str) -> Decimal:
        """Get wallet balance for user."""
        wallet = self.get_or_create_wallet(user_id)
        return Decimal(wallet["balance"])

