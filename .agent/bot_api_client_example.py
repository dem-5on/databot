import os
import hmac
import hashlib
import httpx
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class BackendAPIClient:
    """
    Client for making authenticated requests to the databot backend API.
    
    Automatically handles HMAC signature generation for request authentication.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        secret: Optional[str] = None
    ):
        """
        Initialize the API client.
        
        Args:
            base_url: Backend API base URL (defaults to BACKEND_API_URL env var)
            secret: Shared secret for HMAC (defaults to BOT_BACKEND_SECRET env var)
        """
        self.base_url = (base_url or os.getenv("BACKEND_API_URL", "")).rstrip("/")
        self.secret = secret or os.getenv("BOT_BACKEND_SECRET")
        
        if not self.base_url:
            raise ValueError("BACKEND_API_URL not set in environment")
        if not self.secret:
            raise ValueError("BOT_BACKEND_SECRET not set in environment")
        
        logger.info(f"BackendAPIClient initialized with base_url={self.base_url}")
    
    def _generate_signature(self, user_id: str, platform: str) -> str:
        """
        Generate HMAC-SHA256 signature for request authentication.
        
        Args:
            user_id: User identifier (telegram_id or phone)
            platform: Platform name ("telegram" or "whatsapp")
            
        Returns:
            Hex-encoded HMAC signature
        """
        message = f"{user_id}:{platform}"
        signature = hmac.new(
            self.secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _get_auth_headers(self, user_id: str, platform: str) -> Dict[str, str]:
        """
        Get authentication headers for API request.
        
        Args:
            user_id: User identifier
            platform: Platform name
            
        Returns:
            Dictionary of headers
        """
        return {
            "X-User-ID": str(user_id),
            "X-Platform": platform,
            "X-Signature": self._generate_signature(str(user_id), platform)
        }
    
    async def _make_request(
        self,
        method: str,
        path: str,
        user_id: str,
        platform: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to backend API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., "/api/v1/wallet/balance/123")
            user_id: User identifier for authentication
            platform: Platform name for authentication
            params: Optional query parameters
            json: Optional JSON body
            
        Returns:
            Response JSON
            
        Raises:
            httpx.HTTPError: On HTTP error
        """
        url = f"{self.base_url}{path}"
        headers = self._get_auth_headers(user_id, platform)
        
        logger.debug(f"{method} {url} (user={user_id}, platform={platform})")
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    # -------------------------------------------------------------------------
    # User Management
    # -------------------------------------------------------------------------
    
    async def ensure_telegram_user(
        self,
        telegram_id: str,
        name: Optional[str] = None,
        referral_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ensure Telegram user exists in database.
        
        Args:
            telegram_id: Telegram user ID
            name: Optional user name
            referral_code: Optional referral code for registration
            
        Returns:
            User data with is_new_user flag
        """
        return await self._make_request(
            method="POST",
            path="/api/v1/users/ensure",
            user_id=telegram_id,
            platform="telegram",
            params={
                "telegram_id": telegram_id,
                "name": name,
                "referral_code": referral_code
            }
        )
    
    async def ensure_whatsapp_user(
        self,
        phone: str,
        name: Optional[str] = None,
        referral_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ensure WhatsApp user exists in database.
        
        Args:
            phone: Phone number in E.164 format
            name: Optional user name
            referral_code: Optional referral code for registration
            
        Returns:
            User data with is_new_user flag
        """
        return await self._make_request(
            method="POST",
            path="/api/v1/users/ensure-whatsapp",
            user_id=phone,
            platform="whatsapp",
            json={
                "phone_number": phone,
                "name": name,
                "referral_code": referral_code
            }
        )
    
    async def get_user_history(
        self,
        user_id: str,
        platform: str = "telegram",
        identifier_type: str = "telegram_id",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get user's transaction and order history.
        
        Args:
            user_id: User identifier (telegram_id or phone)
            platform: "telegram" or "whatsapp"
            identifier_type: "telegram_id" or "phone"
            limit: Number of records to return
            
        Returns:
            User history with transactions and orders lists
        """
        return await self._make_request(
            method="GET",
            path=f"/api/v1/users/{user_id}/history",
            user_id=user_id,
            platform=platform,
            params={"identifier_type": identifier_type, "limit": limit}
        )
    
    # -------------------------------------------------------------------------
    # Wallet Operations
    # -------------------------------------------------------------------------
    
    async def get_balance(
        self,
        user_id: str,
        platform: str = "telegram",
        identifier_type: str = "telegram_id"
    ) -> Dict[str, Any]:
        """
        Get user's wallet balance.
        
        Args:
            user_id: User identifier
            platform: "telegram" or "whatsapp"
            identifier_type: "telegram_id" or "phone"
            
        Returns:
            Balance data with user info
        """
        return await self._make_request(
            method="GET",
            path=f"/api/v1/wallet/balance/{user_id}",
            user_id=user_id,
            platform=platform,
            params={"identifier_type": identifier_type}
        )
    
    async def init_deposit(
        self,
        user_id: str,
        amount: float,
        phone: str,
        provider: str,
        platform: str = "telegram"
    ) -> Dict[str, Any]:
        """
        Initialize a deposit transaction.
        
        Args:
            user_id: User identifier (telegram_id or user_id)
            amount: Deposit amount in GHS
            phone: Mobile money phone number
            provider: Network provider (MTN, VODAFONE, AIRTELTIGO)
            platform: "telegram" or "whatsapp"
            
        Returns:
            Deposit initialization response with Paystack details
        """
        payload = {
            "amount": amount,
            "phone": phone,
            "provider": provider
        }
        
        if platform == "telegram":
            payload["telegram_id"] = user_id
        else:
            payload["user_id"] = user_id
        
        return await self._make_request(
            method="POST",
            path="/api/v1/wallet/deposit/init",
            user_id=user_id,
            platform=platform,
            json=payload
        )
    
    async def confirm_deposit(
        self,
        user_id: str,
        reference: str,
        otp: str,
        platform: str = "telegram"
    ) -> Dict[str, Any]:
        """
        Confirm deposit with OTP.
        
        Args:
            user_id: User identifier (for authentication)
            reference: Deposit reference (DEP-xxx)
            otp: OTP code from mobile money prompt
            platform: "telegram" or "whatsapp"
            
        Returns:
            Confirmation response
        """
        return await self._make_request(
            method="POST",
            path="/api/v1/wallet/deposit/confirm",
            user_id=user_id,
            platform=platform,
            json={"reference": reference, "otp": otp}
        )
    
    # -------------------------------------------------------------------------
    # Orders
    # -------------------------------------------------------------------------
    
    async def create_order(
        self,
        user_id: str,
        bundle_id: str,
        phone: str,
        platform: str = "telegram"
    ) -> Dict[str, Any]:
        """
        Create a bundle purchase order.
        
        Args:
            user_id: User identifier
            bundle_id: ID of bundle to purchase
            phone: Phone number to send data to
            platform: "telegram" or "whatsapp"
            
        Returns:
            Order creation response
        """
        payload = {
            "bundle_id": bundle_id,
            "phone": phone
        }
        
        if platform == "telegram":
            payload["telegram_id"] = user_id
        else:
            payload["user_id"] = user_id
        
        return await self._make_request(
            method="POST",
            path="/api/v1/orders",
            user_id=user_id,
            platform=platform,
            json=payload
        )
    
    # -------------------------------------------------------------------------
    # Bundles (No Auth Required)
    # -------------------------------------------------------------------------
    
    async def get_bundles(self, network: Optional[str] = None) -> Dict[str, Any]:
        """
        Get available bundles.
        
        Note: This endpoint doesn't require authentication.
        
        Args:
            network: Optional network filter (MTN, VODAFONE, AIRTELTIGO)
            
        Returns:
            List of available bundles
        """
        params = {"network": network} if network else None
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/bundles",
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    # -------------------------------------------------------------------------
    # Referrals
    # -------------------------------------------------------------------------
    
    async def get_referral_code(
        self,
        user_id: str,
        platform: str = "telegram",
        identifier_type: str = "telegram_id"
    ) -> Dict[str, Any]:
        """
        Get user's referral code.
        
        Args:
            user_id: User identifier
            platform: "telegram" or "whatsapp"
            identifier_type: "telegram_id" or "phone"
            
        Returns:
            Referral code and link
        """
        return await self._make_request(
            method="GET",
            path=f"/api/v1/referrals/code/{user_id}",
            user_id=user_id,
            platform=platform,
            params={"identifier_type": identifier_type}
        )
    
    async def get_referrals(
        self,
        user_id: str,
        platform: str = "telegram",
        identifier_type: str = "telegram_id"
    ) -> Dict[str, Any]:
        """
        Get list of users referred by this user.
        
        Args:
            user_id: User identifier
            platform: "telegram" or "whatsapp"
            identifier_type: "telegram_id" or "phone"
            
        Returns:
            Referrals data with count and details
        """
        return await self._make_request(
            method="GET",
            path=f"/api/v1/referrals/referrals/{user_id}",
            user_id=user_id,
            platform=platform,
            params={"identifier_type": identifier_type}
        )


# Example usage for Telegram bot
async def example_telegram_usage():
    """Example of using the API client in a Telegram bot."""
    api = BackendAPIClient()
    telegram_id = "123456789"
    
    # Ensure user exists
    user = await api.ensure_telegram_user(
        telegram_id=telegram_id,
        name="John Doe"
    )
    print(f"User: {user}")
    
    # Get balance
    balance = await api.get_balance(
        user_id=telegram_id,
        platform="telegram"
    )
    print(f"Balance: {balance['balance']} {balance['currency']}")
    
    # Get bundles
    bundles = await api.get_bundles(network="MTN")
    print(f"Available bundles: {len(bundles['bundles'])}")
    
    # Create order
    order = await api.create_order(
        user_id=telegram_id,
        bundle_id=bundles["bundles"][0]["id"],
        phone="233123456789",
        platform="telegram"
    )
    print(f"Order created: {order}")


# Example usage for WhatsApp bot
async def example_whatsapp_usage():
    """Example of using the API client in a WhatsApp bot."""
    api = BackendAPIClient()
    phone = "233123456789"
    
    # Ensure user exists
    user = await api.ensure_whatsapp_user(
        phone=phone,
        name="Jane Doe"
    )
    print(f"User: {user}")
    
    # Get balance
    balance = await api.get_balance(
        user_id=phone,
        platform="whatsapp",
        identifier_type="phone"
    )
    print(f"Balance: GHS {balance['balance']}")
    
    # Get referral code
    referral = await api.get_referral_code(
        user_id=phone,
        platform="whatsapp",
        identifier_type="phone"
    )
    print(f"Referral code: {referral['referral_code']}")


if __name__ == "__main__":
    import asyncio
    
    # Run examples
    print("=== Telegram Example ===")
    asyncio.run(example_telegram_usage())
    
    print("\n=== WhatsApp Example ===")
    asyncio.run(example_whatsapp_usage())
