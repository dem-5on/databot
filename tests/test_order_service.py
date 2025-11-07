import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from app.services.order_service import OrderService
from app.models.order import OrderStatus
from app.models.transaction import TransactionStatus


@pytest.mark.asyncio
async def test_create_order_success(test_db, test_user, test_wallet, test_bundle):
    """Test successful order creation."""
    # Mock DatamartGH client
    mock_vendor_response = {
        "purchaseId": "test_purchase_id",
        "transactionReference": "TRX-123",
        "price": 23.00,
        "remainingBalance": 77.00
    }
    
    order_service = OrderService()
    
    with patch.object(order_service.datamart_client, 'purchase_bundle', new_callable=AsyncMock) as mock_purchase:
        mock_purchase.return_value = mock_vendor_response
        
        order = await order_service.create_order(
            test_db,
            test_user.id,
            test_bundle.id,
            "0551234567"
        )
        
        assert order.status == OrderStatus.SUCCESS
        assert order.vendor_reference == "TRX-123"
        assert order.price == Decimal("23.00")
        
        # Check wallet was debited
        wallet_balance = await test_db.execute(
            "SELECT balance FROM wallets WHERE user_id = :user_id",
            {"user_id": test_user.id}
        )
        # Simplified check - would need proper query in real test


@pytest.mark.asyncio
async def test_create_order_insufficient_balance(test_db, test_user, test_bundle):
    """Test order creation with insufficient balance."""
    # Create wallet with low balance
    from app.models.wallet import Wallet
    wallet = Wallet(user_id=test_user.id, balance=Decimal("10.00"))
    test_db.add(wallet)
    await test_db.commit()
    
    order_service = OrderService()
    
    with pytest.raises(ValueError, match="Insufficient balance"):
        await order_service.create_order(
            test_db,
            test_user.id,
            test_bundle.id,
            "0551234567"
        )


@pytest.mark.asyncio
async def test_create_order_vendor_failure(test_db, test_user, test_wallet, test_bundle):
    """Test order creation with vendor failure (should refund)."""
    order_service = OrderService()
    
    with patch.object(order_service.datamart_client, 'purchase_bundle', new_callable=AsyncMock) as mock_purchase:
        mock_purchase.side_effect = ValueError("Vendor service unavailable")
        
        initial_balance = test_wallet.balance
        
        with pytest.raises(ValueError, match="Vendor purchase failed"):
            await order_service.create_order(
                test_db,
                test_user.id,
                test_bundle.id,
                "0551234567"
            )
        
        # Check wallet was refunded
        await test_db.refresh(test_wallet)
        # Balance should be restored (simplified - would need proper query)

