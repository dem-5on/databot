import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from app.services.user_service import UserService
from app.repository.order_repo import OrderRepository
from app.repository.transaction_repo import TransactionRepository


logger = logging.getLogger(__name__)
router = APIRouter()


class WhatsAppUserRequest(BaseModel):
    phone_number: str
    name: Optional[str] = None
    referral_code: Optional[str] = None

@router.post("/ensure")
async def ensure_user(
    telegram_id: str,
    name: str = None,
    referral_code: str = None,
):
    """
    Ensure Telegram user exists, create if not.
    Can be called as POST with query params or JSON body.
    If referral_code is provided, register the referral.
    """
    user_service = UserService()
    
    if not telegram_id:
        raise HTTPException(status_code=400, detail="telegram_id is required")
    
    user, is_new_user = await user_service.get_or_create_telegram_user(
        telegram_id=telegram_id,
        name=name,
        referral_code=referral_code
    )
    
    return {
        "user_id": user["id"],
        "telegram_id": user.get("telegram_id"),
        "phone": user.get("phone"),
        "name": user.get("name"),
        "referral_code": user.get("referral_code"),
        "platform": user.get("platform"),
        "is_new_user": is_new_user
    }


@router.post("/ensure-whatsapp")
async def ensure_whatsapp_user(
    request: WhatsAppUserRequest
):
    """
    Ensure WhatsApp user exists, create if not.
    Uses phone number as identifier.
    If referral_code is provided, register the referral.
    """
    logger.info(f"Received WhatsApp user request: phone={request.phone_number}, name={request.name}")

    user_service = UserService()
    
    user, is_new_user = await user_service.get_or_create_whatsapp_user(
        phone_number=request.phone_number,
        name=request.name,
        referral_code=request.referral_code
    )
    
    return {
        "user_id": user["id"],
        "phone": user.get("phone"),
        "name": user.get("name"),
        "referral_code": user.get("referral_code"),
        "platform": user.get("platform"),
        "is_new_user": is_new_user
    }


@router.get("/{identifier}/history")
async def get_user_history(
    identifier: str,
    limit: int = 10,
    identifier_type: str = "telegram_id",  # "telegram_id" or "phone"
):
    """
    Get transaction and order history for user.
    Can use either telegram_id or phone number as identifier.
    """
    user_service = UserService()
    transaction_repo = TransactionRepository()
    order_repo = OrderRepository()
    
    # Get user by identifier type
    if identifier_type == "phone":
        user = await user_service.get_user_by_whatsapp_phone(identifier)
    else:
        user = await user_service.get_user_by_telegram_id(identifier)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get transactions
    transactions = await transaction_repo.get_by_user_id(user["id"], limit=limit)
    
    # Get orders
    orders = await order_repo.get_by_user_id(user["id"], limit=limit)

    return {
        "transactions": [
            {
                "id": t["id"],
                "type": t["type"],
                "amount": t["amount"],
                "currency": t["currency"],
                "status": t["status"],
                "reference": t["reference"],
                "created_at": t.get("created_at")
            }
            for t in transactions
        ],
        "orders": [
            {
                "id": o["id"],
                "bundle_id": o["bundle_id"],
                "phone": o["phone"],
                "price": o["price"],
                "status": o["status"],
                "vendor_reference": o.get("vendor_reference"),
                "created_at": o.get("created_at")
            }
            for o in orders
        ]
    }
