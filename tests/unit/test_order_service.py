import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch


class TestOrderService:
    """Tests for OrderService."""
    
    @pytest.fixture
    def order_service(
        self, 
        mock_bundle_repo, 
        mock_order_repo, 
        mock_transaction_repo, 
        mock_wallet_repo,
        mock_blessdatahub_client,
        mock_notifier
    ):
        """Create OrderService with mocked dependencies."""
        with patch('app.services.order_service.BundleRepository', return_value=mock_bundle_repo), \
             patch('app.services.order_service.OrderRepository', return_value=mock_order_repo), \
             patch('app.services.order_service.TransactionRepository', return_value=mock_transaction_repo), \
             patch('app.services.order_service.BlessdatahubClient', return_value=mock_blessdatahub_client), \
             patch('app.services.order_service.NotifierService', return_value=mock_notifier), \
             patch('app.services.order_service.WalletService') as MockWalletService, \
             patch('app.services.order_service.ReferralService') as MockReferralService:
            
            # Configure WalletService mock
            mock_wallet_service = MagicMock()
            mock_wallet_service.get_balance = AsyncMock(return_value=Decimal("100.00"))
            mock_wallet_service.debit_wallet = AsyncMock(return_value=mock_wallet_repo.debit_balance.return_value)
            mock_wallet_service.refund_wallet = AsyncMock()
            MockWalletService.return_value = mock_wallet_service
            
            # Configure ReferralService mock
            mock_referral_service = MagicMock()
            mock_referral_service.award_referral_bonus = AsyncMock()
            MockReferralService.return_value = mock_referral_service
            
            from app.services.order_service import OrderService
            service = OrderService()
            service.bundle_repo = mock_bundle_repo
            service.order_repo = mock_order_repo
            service.transaction_repo = mock_transaction_repo
            service.blessdatahub_client = mock_blessdatahub_client
            service.wallet_service = mock_wallet_service
            service.referral_service = mock_referral_service
            service.notifier = mock_notifier
            
            return service
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_order_success(self, order_service, mock_bundle_repo, mock_order_repo, mock_blessdatahub_client):
        """Test successful order creation."""
        result = await order_service.create_order(
            user_id="user-123",
            bundle_id="bundle-123",
            phone="233241234567"
        )
        
        # Verify bundle was fetched
        mock_bundle_repo.get_by_id.assert_called_once_with("bundle-123")
        
        # Verify order was created
        mock_order_repo.create_order.assert_called_once()
        
        # Verify vendor was called
        mock_blessdatahub_client.purchase_bundle.assert_called_once()
        
        # Verify wallet was debited
        order_service.wallet_service.debit_wallet.assert_called_once()
        
        assert result["status"] == "success"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_order_bundle_not_found(self, order_service, mock_bundle_repo, mock_notifier):
        """Test order fails when bundle not found."""
        mock_bundle_repo.get_by_id.return_value = None
        
        with pytest.raises(ValueError, match="Bundle not found"):
            await order_service.create_order(
                user_id="user-123",
                bundle_id="invalid-bundle",
                phone="233241234567"
            )
        
        # Verify admin was notified
        mock_notifier.send_admin_alert.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_order_bundle_inactive(self, order_service, mock_bundle_repo, mock_notifier):
        """Test order fails when bundle is inactive."""
        mock_bundle_repo.get_by_id.return_value = {
            "id": "bundle-123",
            "network": "MTN",
            "capacity": 1,
            "price": 5.00,
            "active": False  # Inactive bundle
        }
        
        with pytest.raises(ValueError, match="Bundle not found or inactive"):
            await order_service.create_order(
                user_id="user-123",
                bundle_id="bundle-123",
                phone="233241234567"
            )
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_order_insufficient_balance(self, order_service, mock_bundle_repo, mock_notifier):
        """Test order fails with insufficient balance."""
        # Set wallet balance lower than bundle price
        order_service.wallet_service.get_balance.return_value = Decimal("2.00")
        
        mock_bundle_repo.get_by_id.return_value = {
            "id": "bundle-123",
            "network": "MTN",
            "capacity": 1,
            "price": 5.00,
            "active": True
        }
        
        with pytest.raises(ValueError, match="Insufficient balance"):
            await order_service.create_order(
                user_id="user-123",
                bundle_id="bundle-123",
                phone="233241234567"
            )
        
        # Verify admin was notified
        mock_notifier.send_admin_alert.assert_called()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_order_vendor_failure_triggers_refund(
        self, 
        order_service, 
        mock_bundle_repo, 
        mock_blessdatahub_client,
        mock_order_repo,
        mock_notifier
    ):
        """Test that vendor failure triggers wallet refund."""
        # Make vendor call fail
        mock_blessdatahub_client.purchase_bundle.side_effect = Exception("Vendor error")
        
        with pytest.raises(ValueError, match="Vendor purchase failed"):
            await order_service.create_order(
                user_id="user-123",
                bundle_id="bundle-123",
                phone="233241234567"
            )
        
        # Verify refund was called
        order_service.wallet_service.refund_wallet.assert_called_once()
        
        # Verify order status was updated to failed
        mock_order_repo.update_order_status.assert_called()
        
        # Verify admin was notified
        mock_notifier.send_admin_alert.assert_called()
