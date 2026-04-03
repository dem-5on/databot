import httpx
import logging
from app.core.config import settings
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class BlessdatahubClient:
    """Client for interacting with Blessdatahub API."""
    
    # Class-level shared client for connection pooling
    _client: httpx.AsyncClient = None

    def __init__(self):
        self.base_url = settings.BLESSDATAHUB_API_URL
        self.api_key = settings.BLESSDATAHUB_API_KEY
        self.api_secret = settings.BLESSDATAHUB_API_SECRET
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
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
            logger.info("Created shared BlessdatahubClient httpx client")
        return cls._client
    
    @classmethod
    async def close_client(cls):
        """Close the shared client (call on app shutdown)."""
        if cls._client is not None and not cls._client.is_closed:
            await cls._client.aclose()
            cls._client = None
            logger.info("Closed shared BlessdatahubClient httpx client")

    @staticmethod
    def _map_network_to_blessdatahub(network: str) -> str:
        """Map our network names to Blessdatahub network codes."""
        network_map = {
            "MTN": "MTN",
            "VODAFONE": "Telecel",
            "TELECEL": "Telecel",
            "AIRTELTIGO": "AirtelTigo",
        }
        return network_map.get(network.upper(), "MTN")

    @staticmethod
    def _validate_phone_number(phone_number: str, network: str) -> bool:
        """Validate Ghana phone number against network prefixes."""
        # Remove any spaces or special characters
        clean_number = phone_number.strip().replace(" ", "").replace("-", "")
        
        # Ensure it starts with 0 and is 10 digits
        if not clean_number.startswith("0") or len(clean_number) != 10:
            return False
        
        # Extract prefix (first 3 digits)
        prefix = clean_number[:3]
        
        # Network prefix mapping
        network_prefixes = {
            "MTN": ["024", "025", "053", "054", "055", "059"],
            "TELECEL": ["020", "050"],
            "VODAFONE": ["020", "050"],
            "AIRTELTIGO": ["027", "057", "026", "056"],
        }
        
        valid_prefixes = network_prefixes.get(network.upper(), [])
        return prefix in valid_prefixes

    async def create_order(
        self,
        beneficiary: str,
        package_size: str,
        network: Optional[str] = None
    ) -> Dict:
        """
        Create a single data bundle order.
        
        Args:
            beneficiary: Ghana phone number (e.g., "0247965501")
            package_size: Data package size (e.g., "1GB", "2GB")
            network: Optional network name for validation (MTN, TELECEL, AIRTELTIGO)
            
        Returns:
            API response with status, order_ids, total_cost, new_balance, etc.
            
        Example response:
            {
                "status": "success",
                "processed": 1,
                "total_cost": 4.00,
                "new_balance": 4769.00,
                "order_ids": [74],
                "api_results": [...]
            }
        """
        # Validate phone number if network is provided
        if network and not self._validate_phone_number(beneficiary, network):
            raise ValueError(
                f"Invalid phone number {beneficiary} for network {network}. "
                f"Please check the number format and network prefix."
            )
        
        url = f"{self.base_url}/create_order.php"
        
        payload = {
            "api_key": self.api_key,
            "api_secret": self.api_secret,
            "beneficiary": beneficiary,
            "package_size": package_size
        }
        
        client = await self.get_client()
        
        try:
            response = await client.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=settings.BLESSDATAHUB_PURCHASE_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            
            # Check for API-level errors
            if data.get("status") != "success":
                error_msg = data.get("message", "Unknown error")
                raise ValueError(f"Blessdatahub order creation failed: {error_msg}")
            
            logger.info(
                f"Order created successfully. Order ID: {data.get('order_ids', [])}, "
                f"Cost: {data.get('total_cost')}, Balance: {data.get('new_balance')}"
            )
            
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating order: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            raise

    async def create_bulk_orders(self, orders: List[Dict[str, str]]) -> Dict:
        """
        Create multiple data bundle orders in a single request.
        
        Args:
            orders: List of order dictionaries, each containing:
                - beneficiary: Ghana phone number
                - package_size: Data package size
                
        Example:
            [
                {"beneficiary": "0247965501", "package_size": "1GB"},
                {"beneficiary": "0246145475", "package_size": "2GB"}
            ]
            
        Returns:
            API response with status, processed count, total_cost, order_ids, etc.
        """
        url = f"{self.base_url}/create_order.php"
        
        payload = {
            "api_key": self.api_key,
            "api_secret": self.api_secret,
            "orders": orders
        }
        
        client = await self.get_client()
        
        try:
            response = await client.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=settings.BLESSDATAHUB_PURCHASE_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "success":
                error_msg = data.get("message", "Unknown error")
                raise ValueError(f"Blessdatahub bulk order failed: {error_msg}")
            
            logger.info(
                f"Bulk orders created. Processed: {data.get('processed')}, "
                f"Total cost: {data.get('total_cost')}, Balance: {data.get('new_balance')}"
            )
            
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating bulk orders: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error creating bulk orders: {str(e)}")
            raise

    async def check_order_status(self, order_id: int) -> Dict:
        """
        Check the status of a single order.
        
        Args:
            order_id: The order ID to check
            
        Returns:
            Order status information including:
            - order_id, status, package_size, amount, beneficiary_number
            - network_type, status_description, is_completed, created_at
            
        Example response:
            {
                "success": true,
                "processed": 1,
                "orders": [{
                    "order_id": 123,
                    "status": "delivered",
                    "package_size": "1GB",
                    "amount": 5.50,
                    "beneficiary_number": "0247965501",
                    "network_type": "MTN",
                    "status_description": "Order has been successfully delivered",
                    "is_completed": true,
                    "created_at": "2024-01-15 10:30:00"
                }],
                "api_info": {...}
            }
        """
        url = f"{self.base_url}/check_order_status.php"
        
        params = {
            "order_id": order_id,
            "api_key": self.api_key
        }
        
        client = await self.get_client()
        
        try:
            response = await client.get(
                url,
                params=params,
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                error_msg = data.get("message", "Unknown error")
                raise ValueError(f"Failed to check order status: {error_msg}")
            
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error checking order status: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error checking order status: {str(e)}")
            raise

    async def check_multiple_order_status(self, order_ids: List[int]) -> Dict:
        """
        Check the status of multiple orders.
        
        Args:
            order_ids: List of order IDs to check
            
        Returns:
            Status information for all requested orders
        """
        url = f"{self.base_url}/check_order_status.php"
        
        # Convert list to comma-separated string
        order_ids_str = ",".join(map(str, order_ids))
        
        params = {
            "order_ids": order_ids_str,
            "api_key": self.api_key
        }
        
        client = await self.get_client()
        
        try:
            response = await client.get(
                url,
                params=params,
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                error_msg = data.get("message", "Unknown error")
                raise ValueError(f"Failed to check order statuses: {error_msg}")
            
            logger.info(f"Checked status for {data.get('processed')} orders")
            
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error checking order statuses: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error checking order statuses: {str(e)}")
            raise

    async def purchase_bundle(
        self,
        phone_number: str,
        network: str,
        package_size: str,
        ref: Optional[str] = None
    ) -> Dict:
        """
        Purchase a data bundle (wrapper around create_order for consistency with DatamartClient).
        
        Args:
            phone_number: Recipient phone number (e.g., "0247965501")
            network: Network name (MTN, VODAFONE/TELECEL, AIRTELTIGO)
            package_size: Data package size (e.g., "1GB", "2GB")
            ref: Optional reference (not used by Blessdatahub API, kept for interface compatibility)
            
        Returns:
            Order creation response with order_id, cost, and balance
        """
        return await self.create_order(
            beneficiary=phone_number,
            package_size=package_size,
            network=network
        )