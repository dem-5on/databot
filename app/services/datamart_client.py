import httpx
import logging
from app.core.config import settings
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DatamartClient:
    """Client for interacting with DatamartGH API."""
    
    # Class-level shared client for connection pooling
    _client: httpx.AsyncClient = None

    def __init__(self):
        self.base_url = settings.DATAMART_API_URL
        self.api_key = settings.DATAMART_API_KEY
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
    
    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        """Get or create the shared httpx client with connection pooling."""
        if cls._client is None or cls._client.is_closed:
            cls._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(
                    max_keepalive_connections=settings.MAX_KEEPALIVE_CONNECTIONS,
                    max_connections=settings.MAX_CONNECTIONS
                )
            )
            logger.info("Created shared DatamartClient httpx client")
        return cls._client
    
    @classmethod
    async def close_client(cls):
        """Close the shared client (call on app shutdown)."""
        if cls._client is not None and not cls._client.is_closed:
            await cls._client.aclose()
            cls._client = None
            logger.info("Closed shared DatamartClient httpx client")

    @staticmethod
    def _map_network_to_datamart(network: str) -> str:
        """Map our network names to DatamartGH network codes."""
        network_map = {
            "MTN": "YELLO",
            "VODAFONE": "TELECEL",
            "AIRTELTIGO": "AT_PREMIUM",
        }
        return network_map.get(network.upper(), "YELLO")

    @staticmethod
    def _map_datamart_to_network(datamart_network: str) -> str:
        """Map DatamartGH network codes to our network names."""
        network_map = {
            "YELLO": "MTN",
            "TELECEL": "VODAFONE",
            "AT_PREMIUM": "AIRTELTIGO",
        }
        return network_map.get(datamart_network.upper(), "MTN")

    async def fetch_bundles(self, network: Optional[str] = None) -> List[Dict]:
        """
        Fetch available data bundles from DatamartGH.
        
        Args:
            network: Network name (MTN, VODAFONE, AIRTELTIGO) or None for all networks
            
        Returns:
            List of bundle dictionaries with capacity, mb, price, network
        """
        url = f"{self.base_url}/data-packages"
        params = {}
        
        if network:
            datamart_network = self._map_network_to_datamart(network)
            params["network"] = datamart_network
        
        client = await self.get_client()
        response = await client.get(
            url,
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "success":
            raise ValueError(f"DatamartGH API error: {data.get('message', 'Unknown error')}")
        
        bundles_data = data.get("data", [])
        
        # If network was specified, data is a list
        # If no network, data is a dict with network keys
        if isinstance(bundles_data, dict):
            # Flatten all networks into a single list
            all_bundles = []
            for network_key, bundles in bundles_data.items():
                for bundle in bundles:
                    bundle["network"] = self._map_datamart_to_network(network_key)
                    all_bundles.append(bundle)
            return all_bundles
        else:
            # Map network codes to our format
            for bundle in bundles_data:
                if "network" in bundle:
                    bundle["network"] = self._map_datamart_to_network(bundle["network"])
            return bundles_data

    async def purchase_bundle(
        self,
        phone_number: str,
        network: str,
        capacity: str,
        ref: Optional[str] = None
    ) -> Dict:
        """
        Purchase a data bundle via DatamartGH.
        
        Args:
            phone_number: Recipient phone number (e.g., "0538636317")
            network: Network name (MTN, VODAFONE, AIRTELTIGO)
            capacity: Data capacity in GB as string (e.g., "5")
            ref: Optional reference for tracking
            
        Returns format:
            DatamartGH API response with purchaseId, transactionReference, price, etc.
        """
        datamart_network = self._map_network_to_datamart(network)
        
        payload = {
            "phoneNumber": phone_number,
            "network": datamart_network,
            "capacity": capacity,
            "gateway": "wallet"
        }
        
        client = await self.get_client()
        response = await client.post(
            f"{self.base_url}/purchase",
            json=payload,
            headers=self.headers,
            timeout=settings.PURCHASE_TIMEOUT  # Longer timeout for purchase
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "success":
            error_msg = data.get("message", "Unknown error")
            error_details = data.get("details", {})
            raise ValueError(f"DatamartGH purchase failed: {error_msg}. Details: {error_details}")
        
        return data.get("data", {})