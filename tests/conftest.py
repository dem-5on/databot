import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

import pytest

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Environment variables for testing (set before any app imports)
@pytest.fixture(scope="session", autouse=True)
def mock_env_vars():
    """Set up mock environment variables for testing."""
    env_vars = {
        "ENVIRONMENT": "development",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_KEY": "test_supabase_key",
        "PAYSTACK_SECRET_KEY": "sk_test_dummy",
        "PAYSTACK_PUBLIC_KEY": "pk_test_dummy",
        "TELEGRAM_BOT_TOKEN": "test_bot_token",
        "TELEGRAM_ADMIN_IDS": "123456789",
        "WHATSAPP_BUSINESS_PHONE": "233000000000",
        "WHATSAPP_PHONE_NUMBER_ID": "test_phone_id",
        "WHATSAPP_ACCESS_TOKEN": "test_access_token",
        "WHATSAPP_APP_ID": "test_app_id",
        "WHATSAPP_APP_SECRET": "test_app_secret",
        "WHATSAPP_VERIFY_TOKEN": "test_verify_token",
        "WHATSAPP_ADMIN_NUMBERS": "233000000000",
        "BLESSDATAHUB_API_KEY": "test_api_key",
        "BLESSDATAHUB_API_SECRET": "test_api_secret",
        "BLESSDATAHUB_PURCHASE_TIMEOUT": "60",
        "PURCHASE_TIMEOUT": "60",
        "MINIMUM_DEPOSIT_AMOUNT": "1",
        "REFERRAL_BONUS_AMOUNT": "0.5",
        "PRICE_MARKUP_PERCENTAGE": "10",
        "UVICORN_WORKERS": "1",
        "CELERY_BROKER_URL": "redis://localhost:6379/0",
        "CELERY_RESULT_BACKEND": "redis://localhost:6379/0",
    }
    
    with patch.dict(os.environ, env_vars, clear=False):
        yield


# =====================
# Mock Repository Fixtures
# =====================

@pytest.fixture
def mock_wallet_repo():
    """Mock WalletRepository."""
    repo = MagicMock()
    repo.get_or_create_wallet = AsyncMock(return_value={
        "id": "wallet-123",
        "user_id": "user-123",
        "balance": Decimal("100.00")
    })
    repo.get_by_user_id = AsyncMock(return_value={
        "id": "wallet-123",
        "user_id": "user-123",
        "balance": Decimal("100.00")
    })
    repo.get_balance = AsyncMock(return_value=Decimal("100.00"))
    repo.credit_balance = AsyncMock(return_value={
        "id": "wallet-123",
        "user_id": "user-123",
        "balance": Decimal("150.00")
    })
    repo.debit_balance = AsyncMock(return_value={
        "id": "wallet-123",
        "user_id": "user-123",
        "balance": Decimal("50.00")
    })
    return repo


@pytest.fixture
def mock_transaction_repo():
    """Mock TransactionRepository."""
    repo = MagicMock()
    repo.get_by_reference = AsyncMock(return_value={
        "id": "txn-123",
        "reference": "REF-123",
        "status": "pending",
        "raw_payload": {}
    })
    repo.create_transaction = AsyncMock(return_value={
        "id": "txn-123",
        "reference": "REF-123",
        "status": "pending"
    })
    repo.update_transaction_status = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_bundle_repo():
    """Mock BundleRepository."""
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value={
        "id": "bundle-123",
        "network": "MTN",
        "capacity": 1,
        "price": 5.00,
        "active": True
    })
    repo.get_active_bundles = AsyncMock(return_value=[
        {"id": "bundle-1", "network": "MTN", "capacity": 1, "price": 5.00, "active": True},
        {"id": "bundle-2", "network": "MTN", "capacity": 2, "price": 10.00, "active": True},
    ])
    return repo


@pytest.fixture
def mock_order_repo():
    """Mock OrderRepository."""
    repo = MagicMock()
    repo.create_order = AsyncMock(return_value={
        "id": "order-123",
        "user_id": "user-123",
        "bundle_id": "bundle-123",
        "status": "processing"
    })
    repo.get_by_id = AsyncMock(return_value={
        "id": "order-123",
        "status": "success"
    })
    repo.update_order_status = AsyncMock(return_value=None)
    return repo


# =====================
# Mock Service Fixtures
# =====================

@pytest.fixture
def mock_blessdatahub_client():
    """Mock BlessdatahubClient."""
    client = MagicMock()
    client.purchase_bundle = AsyncMock(return_value={
        "success": True,
        "order_ids": ["vendor-order-123"]
    })
    return client


@pytest.fixture
def mock_notifier():
    """Mock NotifierService."""
    notifier = MagicMock()
    notifier.send_admin_alert = AsyncMock(return_value=None)
    return notifier


# =====================
# Test Data Factories
# =====================

@pytest.fixture
def sample_user():
    """Sample user data."""
    return {
        "id": "user-123",
        "telegram_id": "123456789",
        "name": "Test User",
        "created_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_wallet():
    """Sample wallet data."""
    return {
        "id": "wallet-123",
        "user_id": "user-123",
        "balance": Decimal("100.00")
    }


@pytest.fixture
def sample_bundle():
    """Sample bundle data."""
    return {
        "id": "bundle-123",
        "network": "MTN",
        "capacity": 1,
        "price": 5.00,
        "active": True
    }
