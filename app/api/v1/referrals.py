"""Referral API endpoints using Supabase repositories."""
from fastapi import APIRouter, HTTPException
from app.services.user_service import UserService
from app.services.referral_service import ReferralService

router = APIRouter()


@router.get("/code/{identifier}")
async def get_referral_code(
    identifier: str,
    identifier_type: str = "telegram_id"  # "telegram_id" or "phone"
):
    """Get user's referral code."""
    user_service = UserService()
    referral_service = ReferralService()
    
    # Get user by identifier type
    if identifier_type == "phone":
        user = await user_service.get_user_by_whatsapp_phone(identifier)
    else:
        user = await user_service.get_user_by_telegram_id(identifier)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get or create referral code
    referral_code = await referral_service.get_or_create_referral_code(user["id"])
    
    return {
        "user_id": user["id"],
        "telegram_id": user.get("telegram_id"),
        "phone": user.get("whatsapp_phone"),
        "referral_code": referral_code,
        "referral_link": f"https://t.me/your_bot_username?start={referral_code}"
    }


@router.get("/referrals/{identifier}")
async def get_referrals(
    identifier: str,
    identifier_type: str = "telegram_id"  # "telegram_id" or "phone"
):
    """Get list of users referred by this user."""
    user_service = UserService()
    referral_service = ReferralService()
    
    # Get user by identifier type
    if identifier_type == "phone":
        user = await user_service.get_user_by_whatsapp_phone(identifier)
    else:
        user = await user_service.get_user_by_telegram_id(identifier)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    referrals = await referral_service.get_user_referrals(user["id"])
    
    return {
        "user_id": user["id"],
        "telegram_id": user.get("telegram_id"),
        "phone": user.get("whatsapp_phone"),
        "total_referrals": len(referrals),
        "referrals": referrals
    }
