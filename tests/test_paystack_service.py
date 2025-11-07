import pytest
import hmac
import hashlib
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from app.services.paystack_service import PaystackService


@pytest.fixture
def paystack_service():
    """Create PaystackService instance with test secret key."""
    with patch('app.services.paystack_service.settings') as mock_settings:
        mock_settings.PAYSTACK_SECRET_KEY = "test_secret_key"
        service = PaystackService()
        yield service


class TestPaystackService:
    """Test cases for PaystackService."""

    def test_map_provider_to_paystack(self, paystack_service):
        """Test provider mapping to Paystack format."""
        assert paystack_service._map_provider_to_paystack("MTN") == "mtn"
        assert paystack_service._map_provider_to_paystack("VODAFONE") == "vodafone"
        assert paystack_service._map_provider_to_paystack("AIRTELTIGO") == "tigo"
        assert paystack_service._map_provider_to_paystack("unknown") == "mtn"  # default

    @pytest.mark.asyncio
    async def test_create_mobile_money_charge_amount_conversion(self, paystack_service):
        """Test that GHS amount is correctly converted to pesewas."""
        mock_response = {
            "status": True,
            "message": "Charge initiated",
            "data": {
                "display_text": "You will receive a prompt on your phone",
                "reference": "test_ref_123"
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response_obj)
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            result = await paystack_service.create_mobile_money_charge(
                email="test@example.com",
                amount_ghs=Decimal("50.00"),
                phone="0551234567",
                provider="MTN"
            )
            
            # Verify the call was made with correct amount (5000 pesewas)
            call_args = mock_client_instance.post.call_args
            assert call_args[1]["json"]["amount"] == 5000
            assert call_args[1]["json"]["mobile_money"]["provider"] == "mtn"
            assert result["status"] is True

    def test_verify_webhook_signature_valid(self, paystack_service):
        """Test webhook signature verification with valid signature."""
        body = b'{"event":"charge.success","data":{"reference":"test_ref"}}'
        secret_key = "test_secret_key"
        
        # Compute expected signature
        computed_sig = hmac.new(
            secret_key.encode('utf-8'),
            body,
            hashlib.sha512
        ).hexdigest()
        
        # Verify signature
        assert paystack_service.verify_webhook_signature(body, computed_sig) is True

    def test_verify_webhook_signature_invalid(self, paystack_service):
        """Test webhook signature verification with invalid signature."""
        body = b'{"event":"charge.success","data":{"reference":"test_ref"}}'
        invalid_signature = "invalid_signature_12345"
        
        # Verify signature
        assert paystack_service.verify_webhook_signature(body, invalid_signature) is False

    def test_verify_webhook_signature_empty(self, paystack_service):
        """Test webhook signature verification with empty signature."""
        body = b'{"event":"charge.success"}'
        
        # Verify signature
        assert paystack_service.verify_webhook_signature(body, "") is False

