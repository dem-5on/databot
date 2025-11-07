import uuid
from decimal import Decimal
from sqlalchemy import select
from app.models.wallet import Wallet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import UUID
from app.models.transaction import Transaction, TransactionType, TransactionStatus


class WalletService:
    """Service for wallet operations."""

    @staticmethod
    async def get_or_create_wallet(db: AsyncSession, user_id: UUID) -> Wallet:
        """Get or create wallet for user."""
        stmt = select(Wallet).where(Wallet.user_id == user_id)
        result = await db.execute(stmt)
        wallet = result.scalar_one_or_none()
        
        if not wallet:
            wallet = Wallet(user_id=user_id, balance=Decimal("0.00"))
            db.add(wallet)
            await db.commit()
            await db.refresh(wallet)
        
        return wallet

    @staticmethod
    async def get_balance(db: AsyncSession, user_id: UUID) -> Decimal:
        """Get wallet balance for user."""
        wallet = await WalletService.get_or_create_wallet(db, user_id)
        return wallet.balance

    @staticmethod
    async def credit_wallet(
        db: AsyncSession,
        user_id: UUID,
        amount: Decimal,
        reference: str
    ) -> Wallet:
        """
        Credit wallet with amount (atomic operation with SELECT FOR UPDATE).
        
        Args:
            db: Database session
            user_id: User ID
            amount: Amount to credit
            reference: Transaction reference
            
        Returns:
            Updated wallet
        """
        # Get wallet with row lock to prevent race conditions
        stmt = select(Wallet).where(Wallet.user_id == user_id).with_for_update()
        result = await db.execute(stmt)
        wallet = result.scalar_one_or_none()
        
        if not wallet:
            wallet = Wallet(user_id=user_id, balance=Decimal("0.00"))
            db.add(wallet)
        
        wallet.balance += amount
        
        # Update transaction status
        trans_stmt = select(Transaction).where(Transaction.reference == reference)
        trans_result = await db.execute(trans_stmt)
        transaction = trans_result.scalar_one_or_none()
        
        if transaction:
            transaction.status = TransactionStatus.SUCCESS
            transaction.raw_payload = {"wallet_credited": True, "new_balance": str(wallet.balance)}
        
        await db.commit()
        await db.refresh(wallet)
        
        return wallet

    @staticmethod
    async def debit_wallet(
        db: AsyncSession,
        user_id: UUID,
        amount: Decimal
    ) -> Wallet:
        """
        Debit wallet with amount (atomic operation with SELECT FOR UPDATE).
        
        Args:
            db: Database session
            user_id: User ID
            amount: Amount to debit
            
        Returns:
            Updated wallet
            
        Raises:
            ValueError: If insufficient balance
        """
        # Get wallet with row lock to prevent race conditions
        stmt = select(Wallet).where(Wallet.user_id == user_id).with_for_update()
        result = await db.execute(stmt)
        wallet = result.scalar_one_or_none()
        
        if not wallet:
            raise ValueError("Wallet not found")
        
        if wallet.balance < amount:
            raise ValueError(f"Insufficient balance. Available balance is: {wallet.balance}, Required: {amount}")
        
        wallet.balance -= amount
        
        await db.commit()
        await db.refresh(wallet)
        
        return wallet

    @staticmethod
    async def refund_wallet(
        db: AsyncSession,
        user_id: UUID,
        amount: Decimal,
        transaction_id: UUID
    ) -> Wallet:
        """
        Refund amount to wallet (atomic operation).
        
        Args:
            db: Database session
            user_id: User ID
            amount: Amount to refund
            transaction_id: Original transaction ID
            
        Returns:
            Updated wallet
        """
        # Get wallet with row lock
        stmt = select(Wallet).where(Wallet.user_id == user_id).with_for_update()
        result = await db.execute(stmt)
        wallet = result.scalar_one_or_none()
        
        if not wallet:
            wallet = Wallet(user_id=user_id, balance=Decimal("0.00"))
            db.add(wallet)
        
        wallet.balance += amount
        
        # Create refund transaction
        refund_transaction = Transaction(
            user_id=user_id,
            type=TransactionType.REFUND,
            amount=amount,
            currency="GHS",
            reference=f"REFUND-{uuid.uuid4()}",
            status=TransactionStatus.SUCCESS,
            raw_payload={"original_transaction_id": str(transaction_id)}
        )
        db.add(refund_transaction)
        
        await db.commit()
        await db.refresh(wallet)
        
        return wallet

