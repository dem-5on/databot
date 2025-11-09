import hmac
import httpx
import hashlib
from typing import Dict
from decimal import Decimal
from app.core.config import settings


class PaystackService:
    """Service for interacting with Paystack API for Mobile Money payments."""

    BASE_URL = settings.PAYSTACK_BASE_URL
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _map_provider_to_paystack(provider: str) -> str:
        """Map our provider names to Paystack provider format."""
        provider_map = {
            "MTN": "mtn",
            "VODAFONE": "vod",  # Changed from "vodafone" to "vod"
            "AIRTELTIGO": "tgo",  # Changed from "tigo" to "tgo"
        }
        return provider_map.get(provider.upper(), "mtn")

    async def create_mobile_money_charge(
        self,
        email: str,
        amount_ghs: Decimal,
        phone: str,
        provider: str
    ) -> Dict:
        """
        Create a Mobile Money charge with Paystack.
        
        Args:
            email: User email
            amount_ghs: Amount in Ghana Cedis (GHS)
            phone: Phone number (e.g., "0551234567")
            provider: Provider name (MTN, VODAFONE, AIRTELTIGO)
            
        Returns:
            Paystack API response with charge details including display_text
        """
        # Convert GHS to pesewas (multiply by 100)
        amount_pesewas = int(amount_ghs * 100)
        
        # Map provider to Paystack format
        paystack_provider = self._map_provider_to_paystack(provider)
        
        # Correct payload structure according to Paystack API
        payload = {
            "email": email,
            "amount": str(amount_pesewas),  # Amount as string
            "currency": "GHS",
            "mobile_money": {
                "phone": phone,
                "provider": paystack_provider
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/charge",
                json=payload,
                headers=self.headers,
                timeout=30.0
            )
            
            # Get response data before raising for status
            try:
                data = response.json()
            except Exception:
                # If JSON parsing fails, raise the HTTP error
                response.raise_for_status()
                raise
            
            # Check for HTTP errors
            if response.status_code >= 400:
                error_msg = data.get("message", "Unknown error")
                raise ValueError(f"Paystack API error ({response.status_code}): {error_msg}")
            
            # Check Paystack status
            if not data.get("status"):
                error_msg = data.get("message", "Unknown error")
                raise ValueError(f"Paystack charge failed: {error_msg}")
            
            return data

    def verify_webhook_signature(
        self,
        body: bytes,
        signature_header: str
    ) -> bool:
        """
        Verify Paystack webhook signature using HMAC SHA512.
        
        Args:
            body: Raw request body as bytes
            signature_header: X-Paystack-Signature header value
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not signature_header:
            return False
            
        # Compute HMAC SHA512
        computed_signature = hmac.new(
            self.secret_key.encode('utf-8'),
            body,
            hashlib.sha512
        ).hexdigest()
        
        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(computed_signature, signature_header)

    async def submit_otp(self, reference: str, otp: str) -> Dict:
        """
        Submit OTP for pending mobile money charge.
        
        Args:
            reference: Paystack charge reference
            otp: One-time password from user
            
        Returns:
            Paystack API response
        """
        payload = {
            "otp": otp,
            "reference": reference
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/charge/submit_otp",
                json=payload,
                headers=self.headers,
                timeout=30.0
            )
            
            try:
                data = response.json()
            except Exception:
                response.raise_for_status()
                raise
            
            if response.status_code >= 400:
                error_msg = data.get("message", "Unknown error")
                raise ValueError(f"Paystack OTP submission error: {error_msg}")
            
            return data
    
    async def verify_transaction(self, reference: str) -> Dict:
        """
        Verify a transaction with Paystack by checking its status.
        
        Args:
            reference: Paystack transaction reference
            
        Returns:
            Paystack API response with transaction details
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/transaction/verify/{reference}",
                headers=self.headers,
                timeout=30.0
            )
            
            try:
                data = response.json()
            except Exception:
                response.raise_for_status()
                raise
            
            if response.status_code >= 400:
                error_msg = data.get("message", "Unknown error")
                raise ValueError(f"Paystack verification error ({response.status_code}): {error_msg}")
            
            return data
    
    def format_ghana_phone(self, phone: str) -> str:
       """Convert 0551234567 to +233551234567"""
       if phone.startswith("0"):
           return f"+233{phone[1:]}"
       elif not phone.startswith("+"):
           return f"+233{phone}"
       return phone

