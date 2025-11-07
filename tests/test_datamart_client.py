import pytest
from unittest.mock import AsyncMock, patch
from app.services.datamart_client import DatamartClient


@pytest.fixture
def datamart_client():
    """Create DatamartClient instance with test API key."""
    with patch('app.services.datamart_client.settings') as mock_settings:
        mock_settings.DATAMART_API_URL = "https://api.datamartgh.shop/api/developer"
        mock_settings.DATAMART_API_KEY = "test_api_key"
        client = DatamartClient()
        yield client


class TestDatamartClient:
    """Test cases for DatamartClient."""

    def test_map_network_to_datamart(self, datamart_client):
        """Test network mapping to DatamartGH format."""
        assert datamart_client._map_network_to_datamart("MTN") == "YELLO"
        assert datamart_client._map_network_to_datamart("VODAFONE") == "TELECEL"
        assert datamart_client._map_network_to_datamart("AIRTELTIGO") == "AT_PREMIUM"
        assert datamart_client._map_network_to_datamart("unknown") == "YELLO"  # default

    def test_map_datamart_to_network(self, datamart_client):
        """Test DatamartGH network mapping to our format."""
        assert datamart_client._map_datamart_to_network("YELLO") == "MTN"
        assert datamart_client._map_datamart_to_network("TELECEL") == "VODAFONE"
        assert datamart_client._map_datamart_to_network("AT_PREMIUM") == "AIRTELTIGO"
        assert datamart_client._map_datamart_to_network("unknown") == "MTN"  # default

    @pytest.mark.asyncio
    async def test_fetch_bundles_success(self, datamart_client):
        """Test successful bundle fetching."""
        mock_response = {
            "status": "success",
            "data": [
                {
                    "capacity": "5",
                    "mb": "5000",
                    "price": "23.00",
                    "network": "TELECEL"
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response_obj)
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            result = await datamart_client.fetch_bundles("VODAFONE")
            
            assert len(result) == 1
            assert result[0]["network"] == "VODAFONE"  # Should be mapped
            assert result[0]["capacity"] == "5"

    @pytest.mark.asyncio
    async def test_purchase_bundle_success(self, datamart_client):
        """Test successful bundle purchase."""
        mock_response = {
            "status": "success",
            "data": {
                "purchaseId": "test_purchase_id",
                "transactionReference": "TRX-123",
                "price": 23.00,
                "remainingBalance": 77.00
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response_obj)
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            result = await datamart_client.purchase_bundle(
                phone_number="0551234567",
                network="MTN",
                capacity="5"
            )
            
            assert result["transactionReference"] == "TRX-123"
            assert result["price"] == 23.00

    @pytest.mark.asyncio
    async def test_purchase_bundle_failure(self, datamart_client):
        """Test bundle purchase failure."""
        mock_response = {
            "status": "error",
            "message": "Insufficient balance"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response_obj)
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            with pytest.raises(ValueError, match="DatamartGH purchase failed"):
                await datamart_client.purchase_bundle(
                    phone_number="0551234567",
                    network="MTN",
                    capacity="5"
                )

