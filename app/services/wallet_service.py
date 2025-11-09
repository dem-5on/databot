import uuid
import logging
from decimal import Decimal
from app.repository.wallet_repo import WalletRepository
from app.repository.transaction_repo import TransactionRepository
from app.core.constants import TransactionStatus, TransactionType

logger = logging.getLogger(__name__)
class WalletService:
    """Service for wallet operations using Supabase."""

    def __init__(self):
        self.wallet_repo = WalletRepository()
        self.transaction_repo = TransactionRepository()

    async def get_or_create_wallet(self, user_id: str) -> dict:
        """Get or create wallet for user."""
        return await self.wallet_repo.get_or_create_wallet(user_id)

    async def get_balance(self, user_id: str) -> Decimal:
        """Get wallet balance for user."""
        return await self.wallet_repo.get_balance(user_id)

    async def credit_wallet(
        self,
        user_id: str,
        amount: Decimal,
        reference: str
    ) -> dict:
        """
        Credit wallet with amount (idempotent operation).
        
        This method is idempotent - it checks transaction status before crediting
        to prevent double crediting if both webhook and manual verification fire.
        
        Args:
            user_id: User ID
            amount: Amount to credit
            reference: Transaction reference
            
        Returns:
            Updated wallet
            
        Raises:
            ValueError: If transaction is already processed (idempotency check)
        """
       
        
        # First, check transaction status to prevent double crediting
        transaction = await self.transaction_repo.get_by_reference(reference)
        if not transaction:
            raise ValueError(f"Transaction not found: {reference}")
        
        # IDEMPOTENCY CHECK: If transaction is already SUCCESS, don't credit again
        if transaction["status"] == TransactionStatus.SUCCESS.value:
            # Check if wallet was already credited by looking at payload
            raw_payload = transaction.get("raw_payload") or {}
            if isinstance(raw_payload, dict) and raw_payload.get("wallet_credited"):
                logger.info(f"Transaction {reference} already processed and wallet credited. Skipping credit.")
                # Return existing wallet without crediting
                wallet = self.wallet_repo.get_by_user_id(user_id)
                if not wallet:
                    wallet = self.wallet_repo.get_or_create_wallet(user_id)
                return wallet
            else:
                # Status is SUCCESS but payload doesn't indicate credit - this is unusual
                # Log warning but don't credit to be safe
                logger.warning(
                    f"Transaction {reference} has SUCCESS status but no wallet_credited flag. "
                    f"Skipping credit to prevent double crediting."
                )
                wallet = await self.wallet_repo.get_by_user_id(user_id)
                if not wallet:
                    wallet = await self.wallet_repo.get_or_create_wallet(user_id)
                return wallet
        
        # If transaction is FAILED, don't credit
        if transaction["status"] == TransactionStatus.FAILED.value:
            raise ValueError(f"Transaction {reference} has failed status. Cannot credit wallet.")
        
        # Transaction is pending/processing - proceed with credit
        # Get or create wallet
        wallet = await self.wallet_repo.get_or_create_wallet(user_id)
        
        # Credit balance
        wallet = await self.wallet_repo.credit_balance(wallet["id"], amount)

        # Update transaction status to SUCCESS
        # Re-check status before updating to handle race conditions
        try:
            # Re-fetch transaction to check if another process already updated it
            updated_transaction = await self.transaction_repo.get_by_reference(reference)
            if updated_transaction and updated_transaction["status"] == TransactionStatus.SUCCESS.value:
                # Another process already processed this - rollback the credit
                logger.warning(
                    f"Transaction {reference} was already processed by another process. "
                    f"Rolling back credit to prevent double crediting."
                )
                # Debit the amount we just credited
                try:
                    await self.wallet_repo.debit_balance(wallet["id"], amount)
                except ValueError as e:
                    # If debit fails (insufficient balance), log error
                    logger.error(f"Failed to rollback credit for transaction {reference}: {e}")
                
                # Return wallet without the credit
                return (await self.wallet_repo.get_by_user_id(user_id))
            
            # Safe to update transaction status
            current_payload = transaction.get("raw_payload") or {}
            if isinstance(current_payload, dict):
                current_payload["wallet_credited"] = True
                current_payload["new_balance"] = str(wallet["balance"])
                current_payload["credited_at"] = transaction.get("updated_at") or transaction.get("created_at")
            else:
                current_payload = {
                    "wallet_credited": True,
                    "new_balance": str(wallet["balance"])
                }
            
            await self.transaction_repo.update_transaction_status(
                transaction["id"],
                TransactionStatus.SUCCESS.value,
                raw_payload=current_payload
            )
            
            logger.info(f"Wallet credited for transaction {reference}. Amount: {amount}, New balance: {wallet['balance']}")
            
        except Exception as e:
            # If transaction update fails, we've already credited the wallet
            # Log error but don't fail - the wallet credit is more important
            logger.error(f"Failed to update transaction status for {reference}: {e}")
        
        return wallet

    async def debit_wallet(
        self,
        user_id: str,
        amount: Decimal
    ) -> dict:
        """
        Debit wallet with amount.
        
        Args:
            user_id: User ID
            amount: Amount to debit
            
        Returns:
            Updated wallet
            
        Raises:
            ValueError: If insufficient balance
        """
        # Get wallet
        wallet = await self.wallet_repo.get_by_user_id(user_id)
        if not wallet:
            raise ValueError("Wallet not found")
        
        # Debit balance (this will raise ValueError if insufficient)
        wallet = await self.wallet_repo.debit_balance(wallet["id"], amount)
        
        return wallet

    async def refund_wallet(
        self,
        user_id: str,
        amount: Decimal,
        transaction_id: str
    ) -> dict:
        """
        Refund amount to wallet.
        
        Args:
            user_id: User ID
            amount: Amount to refund
            transaction_id: Original transaction ID
            
        Returns:
            Updated wallet
        """
        # Get or create wallet
        wallet = await self.wallet_repo.get_or_create_wallet(user_id)
        
        # Credit balance
        wallet = await self.wallet_repo.credit_balance(wallet["id"], amount)
        
        # Create refund transaction
        await self.transaction_repo.create_transaction(
            user_id=user_id,
            transaction_type=TransactionType.REFUND.value,
            amount=amount,
            currency="GHS",
            reference=f"REFUND-{uuid.uuid4()}",
            status=TransactionStatus.SUCCESS.value,
            raw_payload={"original_transaction_id": transaction_id}
        )
        
        return wallet
