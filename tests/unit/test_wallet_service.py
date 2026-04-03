import pytest
from decimal import Decimal
from unittest.mock import AsyncMock,patch


class TestWalletService:
    """Tests for WalletService."""
    
    @pytest.fixture
    def wallet_service(self, mock_wallet_repo, mock_transaction_repo):
        """Create WalletService with mocked dependencies."""
        with patch('app.services.wallet_service.WalletRepository', return_value=mock_wallet_repo), \
             patch('app.services.wallet_service.TransactionRepository', return_value=mock_transaction_repo):
            from app.services.wallet_service import WalletService
            service = WalletService()
            service.wallet_repo = mock_wallet_repo
            service.transaction_repo = mock_transaction_repo
            return service
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_or_create_wallet_existing(self, wallet_service, mock_wallet_repo):
        """Test getting an existing wallet."""
        result = await wallet_service.get_or_create_wallet("user-123")
        
        mock_wallet_repo.get_or_create_wallet.assert_called_once_with("user-123")
        assert result["user_id"] == "user-123"
        assert result["balance"] == Decimal("100.00")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_balance(self, wallet_service, mock_wallet_repo):
        """Test getting wallet balance."""
        result = await wallet_service.get_balance("user-123")
        
        mock_wallet_repo.get_balance.assert_called_once_with("user-123")
        assert result == Decimal("100.00")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_debit_wallet_success(self, wallet_service, mock_wallet_repo):
        """Test successful wallet debit."""
        result = await wallet_service.debit_wallet("user-123", Decimal("50.00"))
        
        mock_wallet_repo.get_by_user_id.assert_called_once_with("user-123")
        mock_wallet_repo.debit_balance.assert_called_once()
        assert result["balance"] == Decimal("50.00")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_debit_wallet_no_wallet(self, wallet_service, mock_wallet_repo):
        """Test debit fails when wallet not found."""
        mock_wallet_repo.get_by_user_id.return_value = None
        
        with pytest.raises(ValueError, match="Wallet not found"):
            await wallet_service.debit_wallet("user-123", Decimal("50.00"))
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refund_wallet_success(self, wallet_service, mock_wallet_repo, mock_transaction_repo):
        """Test successful wallet refund."""
        result = await wallet_service.refund_wallet(
            user_id="user-123",
            amount=Decimal("25.00"),
            transaction_id="txn-original"
        )
        
        mock_wallet_repo.get_or_create_wallet.assert_called_once()
        mock_wallet_repo.credit_balance.assert_called_once()
        mock_transaction_repo.create_transaction.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_credit_wallet_already_processed(self, wallet_service, mock_wallet_repo, mock_transaction_repo):
        """Test credit is skipped for already processed transaction."""
        # Set up transaction as already processed
        mock_transaction_repo.get_by_reference.return_value = {
            "id": "txn-123",
            "reference": "REF-123",
            "status": "success",
            "raw_payload": {"wallet_credited": True},
            "updated_at": "2024-01-01T00:00:00Z"
        }
        
        # Mock the wallet_lock context manager
        with patch('app.services.wallet_service.wallet_lock') as mock_lock:
            mock_lock.return_value.__aenter__ = AsyncMock()
            mock_lock.return_value.__aexit__ = AsyncMock()
            
            result = await wallet_service.credit_wallet(
                user_id="user-123",
                amount=Decimal("50.00"),
                reference="REF-123"
            )
        
        # Should not credit again
        mock_wallet_repo.credit_balance.assert_not_called()
