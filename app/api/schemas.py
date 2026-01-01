"""
Response Data Transfer Objects (DTOs) for API endpoints.

These Pydantic models ensure consistent, type-safe responses across the API
and prevent accidental exposure of internal fields.
"""

from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class BalanceResponseDTO(BaseModel):
    """Response DTO for wallet balance endpoint."""
    
    user_id: str = Field(..., description="User's unique identifier")
    telegram_id: Optional[str] = Field(None, description="Telegram ID if user has Telegram account")
    phone: Optional[str] = Field(None, description="Phone number if user has WhatsApp account")
    balance: str = Field(..., description="Current wallet balance")
    currency: str = Field(default="GHS", description="Currency code")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "telegram_id": "123456789",
            "phone": "233123456789",
            "balance": "50.00",
            "currency": "GHS"
        }
    })


class TransactionHistoryItemDTO(BaseModel):
    """Individual transaction in history."""
    
    id: str
    type: str = Field(..., description="Transaction type (deposit, purchase, refund)")
    amount: str = Field(..., description="Transaction amount")
    currency: str = Field(default="GHS")
    status: str = Field(..., description="Transaction status")
    reference: str
    created_at: Optional[str] = None


class OrderHistoryItemDTO(BaseModel):
    """Individual order in history."""
    
    id: str
    bundle_id: str
    phone: str = Field(..., description="Phone number data was sent to")
    price: str
    status: str
    delivery_status: str = Field(..., description="Vendor delivery status")
    vendor_reference: Optional[str] = None
    created_at: Optional[str] = None


class UserHistoryResponseDTO(BaseModel):
    """Response DTO for user history endpoint."""
    
    user_id: str
    transactions: List[TransactionHistoryItemDTO] = Field(default_factory=list)
    orders: List[OrderHistoryItemDTO] = Field(default_factory=list)
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "transactions": [
                {
                    "id": "1",
                    "type": "deposit",
                    "amount": "50.00",
                    "currency": "GHS",
                    "status": "success",
                    "reference": "DEP-123",
                    "created_at": "2025-12-30T01:00:00Z"
                }
            ],
            "orders": [
                {
                    "id": "1",
                    "bundle_id": "bundle-123",
                    "phone": "233123456789",
                    "price": "5.00",
                    "status": "completed",
                    "vendor_reference": "VEN-456",
                    "created_at": "2025-12-30T01:05:00Z"
                }
            ]
        }
    })


class ReferralCodeResponseDTO(BaseModel):
    """Response DTO for referral code endpoint."""
    
    user_id: str
    telegram_id: Optional[str] = None
    phone: Optional[str] = None
    referral_code: str
    referral_link: str = Field(..., description="Full referral link for sharing")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "telegram_id": "123456789",
            "phone": None,
            "referral_code": "ABC123",
            "referral_link": "https://t.me/your_bot?start=ABC123"
        }
    })


class ReferralItemDTO(BaseModel):
    """Individual referral record."""
    
    id: str
    referred_user_id: str
    referred_at: Optional[str] = None
    bonus_awarded: bool = Field(default=False)


class UserReferralsResponseDTO(BaseModel):
    """Response DTO for user referrals endpoint."""
    
    user_id: str
    telegram_id: Optional[str] = None
    phone: Optional[str] = None
    total_referrals: int = Field(..., description="Total number of users referred")
    referrals: List[ReferralItemDTO] = Field(default_factory=list)
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "telegram_id": "123456789",
            "phone": None,
            "total_referrals": 3,
            "referrals": [
                {
                    "id": "1",
                    "referred_user_id": "other-user-id",
                    "referred_at": "2025-12-29T12:00:00Z",
                    "bonus_awarded": True
                }
            ]
        }
    })


class OrderResponseDTO(BaseModel):
    """Response DTO for order creation."""
    
    status: str = Field(..., description="Request status")
    order_id: str
    order_status: str = Field(..., description="Order processing status")
    delivery_status: str = Field(default="pending", description="Vendor delivery status")
    vendor_reference: Optional[str] = None
    message: Optional[str] = Field(None, description="Human-readable message")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "status": "success",
            "order_id": "550e8400-e29b-41d4-a716-446655440000",
            "order_status": "processing",
            "vendor_reference": "VEN-12345",
            "message": "Order created successfully"
        }
    })


class BundleDTO(BaseModel):
    """Bundle information DTO."""
    
    id: str
    network: str = Field(..., description="Network provider (MTN, VODAFONE, AIRTELTIGO)")
    capacity: str = Field(..., description="Data capacity (e.g., '1GB', '5GB')")
    mb: int = Field(..., description="Megabytes")
    price: str = Field(..., description="Price in GHS (includes markup)")
    currency: str = Field(default="GHS")


class BundlesResponseDTO(BaseModel):
    """Response DTO for bundles list."""
    
    bundles: List[BundleDTO] = Field(default_factory=list)
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "bundles": [
                {
                    "id": "bundle-1",
                    "network": "MTN",
                    "capacity": "1GB",
                    "mb": 1024,
                    "price": "5.50",
                    "currency": "GHS"
                }
            ]
        }
    })
