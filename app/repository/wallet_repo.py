import logging
from decimal import Decimal
from typing import Optional, Dict, Any
from postgrest.exceptions import APIError
from app.repository.base import BaseRepository

logger = logging.getLogger(__name__)


class WalletRepository(BaseRepository):
    """Repository for wallet operations with atomic balance updates."""
    
    def __init__(self):
        super().__init__("wallets")
    
    async def get_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get wallet by user ID."""
        return await self.get_by_field("user_id", user_id)
    
    async def create_wallet(self, user_id: str) -> Dict[str, Any]:
        """
        Create a new wallet for a user.
        
        Args:
            user_id: The user ID to create wallet for
            
        Returns:
            The created wallet
            
        Raises:
            ValueError: If wallet creation fails
        """
        try:
            wallet_data = {
                "user_id": user_id,
                "balance": "0.00"
            }
            wallet = await self.create(wallet_data)
            logger.info(f"Created wallet for user {user_id}")
            return wallet
        except APIError as e:
            logger.error(f"API error creating wallet for user {user_id}: {str(e)}")
            raise ValueError(f"Failed to create wallet: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating wallet for user {user_id}: {str(e)}")
            raise ValueError(f"Error creating wallet: {str(e)}")

    async def get_or_create_wallet(self, user_id: str) -> Dict[str, Any]:
        """
        Get existing wallet or create a new one if it doesn't exist.
        
        Args:
            user_id: The user ID
            
        Returns:
            The wallet record
        """
        wallet = await self.get_by_user_id(user_id)
        if not wallet:
            wallet = await self.create_wallet(user_id)
        return wallet

    async def update_balance(self, wallet_id: str, new_balance: Decimal) -> Dict[str, Any]:
        """
        Update wallet balance directly (use with caution - prefer credit/debit).
        
        Args:
            wallet_id: The wallet ID
            new_balance: The new balance to set
            
        Returns:
            The updated wallet
            
        Raises:
            ValueError: If wallet not found or update fails
        """
        wallet = await self.get_by_id(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet not found: {wallet_id}")
        
        return await self.update(wallet_id, {"balance": str(new_balance)})
    
    async def credit_balance(self, wallet_id: str, amount: Decimal) -> Dict[str, Any]:
        """
        Credit wallet balance using atomic database operation.
        
        This method uses Supabase RPC to perform atomic balance updates,
        preventing race conditions when multiple credits happen simultaneously.
        
        Args:
            wallet_id: The wallet ID
            amount: The amount to credit (must be positive)
            
        Returns:
            The updated wallet
            
        Raises:
            ValueError: If wallet not found, amount invalid, or operation fails
        """
        if amount <= 0:
            raise ValueError(f"Credit amount must be positive, got: {amount}")
        
        try:
            # Use Supabase RPC for atomic operation
            result = await self.client.rpc(
                'credit_wallet',
                {
                    'wallet_id_param': wallet_id,
                    'amount_param': str(amount)
                }
            )
            
            if not result:
                raise ValueError(f"Failed to credit wallet {wallet_id}")
            
            logger.info(f"Credited {amount} to wallet {wallet_id}")
            
            # Return the updated wallet
            return await self.get_by_id(wallet_id)
            
        except APIError as e:
            # If RPC doesn't exist, fall back to traditional method with warning
            logger.warning(f"RPC 'credit_wallet' not found, using fallback method: {str(e)}")
            return await self._credit_balance_fallback(wallet_id, amount)
        except Exception as e:
            logger.error(f"Error crediting wallet {wallet_id}: {str(e)}")
            raise ValueError(f"Error crediting wallet: {str(e)}")
    
    
    
    async def debit_balance(self, wallet_id: str, amount: Decimal) -> Dict[str, Any]:
        """
        Debit wallet balance using atomic database operation with balance check.
        
        This method uses Supabase RPC to perform atomic balance updates,
        preventing race conditions and ensuring sufficient balance.
        
        Args:
            wallet_id: The wallet ID
            amount: The amount to debit (must be positive)
            
        Returns:
            The updated wallet
            
        Raises:
            ValueError: If wallet not found, insufficient balance, amount invalid, or operation fails
        """
        if amount <= 0:
            raise ValueError(f"Debit amount must be positive, got: {amount}")
        
        try:
            # Use Supabase RPC for atomic operation with balance check
            result = await self.client.rpc(
                'debit_wallet',
                {
                    'wallet_id_param': wallet_id,
                    'amount_param': str(amount)
                }
            )
            
            if not result:
                raise ValueError(f"Failed to debit wallet {wallet_id}")
            
            logger.info(f"Debited {amount} from wallet {wallet_id}")
            
            # Return the updated wallet
            return await self.get_by_id(wallet_id)
            
        except APIError as e:
            error_msg = str(e)
            if "insufficient balance" in error_msg.lower():
                logger.error(f"Insufficient balance in wallet {wallet_id}")
            
            # If RPC doesn't exist, fall back to traditional method with warning
            logger.warning(f"RPC 'debit_wallet' not found, using fallback method: {error_msg}")
            return await self._debit_balance_fallback(wallet_id, amount)
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error debiting wallet {wallet_id}: {str(e)}")
            raise ValueError(f"Error debiting wallet: {str(e)}")
    
    async def _credit_balance_fallback(self, wallet_id: str, amount: Decimal) -> Dict[str, Any]:
        """
        Fallback method for crediting balance (less safe, prone to race conditions).
        """
        wallet = await self.get_by_id(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet not found: {wallet_id}")
        
        # Ensure consistent Decimal arithmetic
        amount = Decimal(str(amount))
        current_balance = Decimal(str(wallet["balance"]))
        new_balance = current_balance + amount
        
        logger.warning(f"Using fallback credit method for wallet {wallet_id} (race condition risk)")
        return await self.update(wallet_id, {"balance": str(new_balance)})

    async def _debit_balance_fallback(self, wallet_id: str, amount: Decimal) -> Dict[str, Any]:
        """
        Fallback method for debiting balance (less safe, prone to race conditions).
        """
        wallet = await self.get_by_id(wallet_id)
        if not wallet:
            raise ValueError(f"Wallet not found: {wallet_id}")

        # Ensure consistent Decimal arithmetic
        amount = Decimal(str(amount))
        current_balance = Decimal(str(wallet["balance"]))
        
        if current_balance < amount:
            logger.error(f"Insufficient balance. Available: {current_balance}, Required: {amount}")
            raise ValueError("Insufficient balance to complete this transaction.")

        new_balance = current_balance - amount
        
        logger.warning(f"Using fallback debit method for wallet {wallet_id} (race condition risk)")
        return await self.update(wallet_id, {"balance": str(new_balance)})

    
    async def get_balance(self, user_id: str) -> Decimal:
        """
        Get wallet balance for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            The current balance
        """
        wallet = await self.get_or_create_wallet(user_id)
        return Decimal(wallet["balance"])
    
    async def has_sufficient_balance(self, user_id: str, required_amount: Decimal) -> bool:
        """
        Check if user has sufficient balance for a transaction.
        
        Args:
            user_id: The user ID
            required_amount: The amount needed
            
        Returns:
            True if balance is sufficient, False otherwise
        """
        try:
            current_balance = await self.get_balance(user_id)
            return current_balance >= required_amount
        except Exception as e:
            logger.error(f"Error checking balance for user {user_id}: {str(e)}")
            return False
    
    async def transfer_balance(
        self, 
        from_wallet_id: str, 
        to_wallet_id: str, 
        amount: Decimal
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Transfer balance between two wallets atomically.
        
        Args:
            from_wallet_id: Source wallet ID
            to_wallet_id: Destination wallet ID
            amount: Amount to transfer
            
        Returns:
            Tuple of (updated_from_wallet, updated_to_wallet)
            
        Raises:
            ValueError: If transfer fails
        """
        if amount <= 0:
            raise ValueError(f"Transfer amount must be positive, got: {amount}")
        
        try:
            # Debit from source wallet (includes balance check)
            from_wallet = await self.debit_balance(from_wallet_id, amount)
            
            try:
                # Credit to destination wallet
                to_wallet = await self.credit_balance(to_wallet_id, amount)
                
                logger.info(f"Transferred {amount} from {from_wallet_id} to {to_wallet_id}")
                return from_wallet, to_wallet
                
            except Exception as e:
                # Rollback: Credit back to source wallet
                logger.error(f"Transfer failed, rolling back: {str(e)}")
                await self.credit_balance(from_wallet_id, amount)
                raise ValueError(f"Transfer failed: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error transferring balance: {str(e)}")
            raise
