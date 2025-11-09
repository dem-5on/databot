"""User API endpoints using Supabase repositories."""
from fastapi import APIRouter, HTTPException
from app.repository.user_repo import UserRepository
from app.repository.order_repo import OrderRepository
from app.repository.transaction_repo import TransactionRepository
from app.services.referral_service import ReferralService

router = APIRouter()


@router.post("/ensure")
async def ensure_user(
    telegram_id: str,
    name: str = None,
    referral_code: str = None,
):
    """
    Ensure user exists, create if not.
    Can be called as POST with query params or JSON body.
    If referral_code is provided, register the referral.
    """
    user_repo = UserRepository()
    referral_service = ReferralService()
    
    user, is_new_user = user_repo.get_or_create(telegram_id, name)
    
    if is_new_user:
        # Generate referral code for new user
        await referral_service.get_or_create_referral_code(user["id"])
        
        # Register referral if code was provided
        if referral_code:
            await referral_service.register_referral(user["id"], referral_code)
        
        # Refresh user to get updated data
        user = user_repo.get_by_id(user["id"])
    
    return {
        "user_id": user["id"],
        "telegram_id": user["telegram_id"],
        "name": user.get("name"),
        "referral_code": user.get("referral_code"),
        "is_new_user": is_new_user
    }


@router.get("/{telegram_id}/history")
async def get_user_history(
    telegram_id: str,
    limit: int = 10,
):
    """
    Get transaction and order history for user.
    """
    user_repo = UserRepository()
    transaction_repo = TransactionRepository()
    order_repo = OrderRepository()
    
    # Get user
    user = user_repo.get_by_telegram_id(telegram_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get transactions
    transactions = transaction_repo.get_by_user_id(user["id"], limit=limit)
    
    # Get orders
    orders = order_repo.get_by_user_id(user["id"], limit=limit)
    
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
