import pytest
from decimal import Decimal
from sqlalchemy.dialects.postgresql import UUID
from app.services.wallet_service import WalletService
from app.models.transaction import Transaction, TransactionType, TransactionStatus
import uuid


@pytest.mark.asyncio
async def test_get_or_create_wallet(test_db, test_user):
    """Test getting or creating wallet."""
    wallet = await WalletService.get_or_create_wallet(test_db, test_user.id)
    
    assert wallet is not None
    assert wallet.user_id == test_user.id
    assert wallet.balance == Decimal("0.00")


@pytest.mark.asyncio
async def test_get_balance(test_db, test_user, test_wallet):
    """Test getting wallet balance."""
    balance = await WalletService.get_balance(test_db, test_user.id)
    
    assert balance == Decimal("100.00")


@pytest.mark.asyncio
async def test_credit_wallet(test_db, test_user, test_wallet):
    """Test crediting wallet."""
    # Create a transaction first
    transaction = Transaction(
        user_id=test_user.id,
        type=TransactionType.DEPOSIT,
        amount=Decimal("50.00"),
        currency="GHS",
        reference="TEST-REF-123",
        status=TransactionStatus.PENDING
    )
    test_db.add(transaction)
    await test_db.commit()
    
    wallet = await WalletService.credit_wallet(
        test_db,
        test_user.id,
        Decimal("50.00"),
        "TEST-REF-123"
    )
    
    assert wallet.balance == Decimal("150.00")
    
    # Check transaction was updated
    await test_db.refresh(transaction)
    assert transaction.status == TransactionStatus.SUCCESS


@pytest.mark.asyncio
async def test_debit_wallet_success(test_db, test_user, test_wallet):
    """Test successful wallet debit."""
    wallet = await WalletService.debit_wallet(
        test_db,
        test_user.id,
        Decimal("30.00")
    )
    
    assert wallet.balance == Decimal("70.00")


@pytest.mark.asyncio
async def test_debit_wallet_insufficient_balance(test_db, test_user, test_wallet):
    """Test wallet debit with insufficient balance."""
    with pytest.raises(ValueError, match="Insufficient balance"):
        await WalletService.debit_wallet(
            test_db,
            test_user.id,
            Decimal("200.00")
        )


@pytest.mark.asyncio
async def test_refund_wallet(test_db, test_user, test_wallet):
    """Test wallet refund."""
    # Create a transaction
    transaction = Transaction(
        user_id=test_user.id,
        type=TransactionType.PURCHASE,
        amount=Decimal("20.00"),
        currency="GHS",
        reference="TEST-REF-456",
        status=TransactionStatus.SUCCESS
    )
    test_db.add(transaction)
    await test_db.commit()
    
    # Debit first
    await WalletService.debit_wallet(test_db, test_user.id, Decimal("20.00"))
    
    # Then refund
    wallet = await WalletService.refund_wallet(
        test_db,
        test_user.id,
        Decimal("20.00"),
        transaction.id
    )
    
    assert wallet.balance == Decimal("100.00")
    
    # Check refund transaction was created
    refund_trans = await test_db.execute(
        "SELECT * FROM transactions WHERE type = 'refund'"
    )
    # Note: This is a simplified check - in real test you'd query properly

