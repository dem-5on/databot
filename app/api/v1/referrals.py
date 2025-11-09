"""Referral API endpoints using Supabase repositories."""
from fastapi import APIRouter, HTTPException
from app.repository.user_repo import UserRepository
from app.services.referral_service import ReferralService

router = APIRouter()


@router.get("/code/{telegram_id}")
async def get_referral_code(telegram_id: str):
    """Get user's referral code."""
    user_repo = UserRepository()
    referral_service = ReferralService()
    
    user = await user_repo.get_by_telegram_id(telegram_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get or create referral code
    referral_code = await referral_service.get_or_create_referral_code(user["id"])
    
    return {
        "telegram_id": telegram_id,
        "referral_code": referral_code,
        "referral_link": f"https://t.me/your_bot_username?start={referral_code}"
    }


@router.get("/referrals/{telegram_id}")
async def get_referrals(telegram_id: str):
    """Get list of users referred by this user."""
    user_repo = UserRepository()
    referral_service = ReferralService()
    
    user = await user_repo.get_by_telegram_id(telegram_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    referrals = await referral_service.get_user_referrals(user["id"])
    
    return {
        "telegram_id": telegram_id,
        "total_referrals": len(referrals),
        "referrals": referrals
    }
