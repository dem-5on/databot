"""Referral API endpoints using Supabase repositories."""
from fastapi import APIRouter, HTTPException, Depends, Request
from app.core.auth import verify_user_access
from app.core.rate_limit import limiter
from app.api.schemas import ReferralCodeResponseDTO, UserReferralsResponseDTO, ReferralItemDTO
from app.services.user_service import UserService
from app.services.referral_service import ReferralService

router = APIRouter()


@router.get("/code/{identifier}", response_model=ReferralCodeResponseDTO)
@limiter.limit("30/minute")
async def get_referral_code(
    request: Request,
    identifier: str = Depends(verify_user_access),
    identifier_type: str = "telegram_id"  # "telegram_id" or "phone"
):
    """
    Get authenticated user's referral code.
    
    Requires authentication via X-User-ID, X-Platform, and X-Signature headers.
    Users can only get their own referral code.
    """
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
    
    return ReferralCodeResponseDTO(
        user_id=user["id"],
        telegram_id=user.get("telegram_id"),
        phone=user.get("whatsapp_phone"),
        referral_code=referral_code,
        referral_link=f"https://t.me/your_bot_username?start={referral_code}"
    )


@router.get("/referrals/{identifier}", response_model=UserReferralsResponseDTO)
@limiter.limit("30/minute")
async def get_referrals(
    request: Request,
    identifier: str = Depends(verify_user_access),
    identifier_type: str = "telegram_id"  # "telegram_id" or "phone"
):
    """
    Get list of users referred by authenticated user.
    
    Requires authentication via X-User-ID, X-Platform, and X-Signature headers.
    Users can only see their own referrals.
    """
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
    
    return UserReferralsResponseDTO(
        user_id=user["id"],
        telegram_id=user.get("telegram_id"),
        phone=user.get("whatsapp_phone"),
        total_referrals=len(referrals),
        referrals=[
            ReferralItemDTO(
                id=r.get("id", ""),
                referred_user_id=r.get("referred_id", ""),
                referred_at=r.get("created_at"),
                bonus_awarded=r.get("bonus_awarded", False)
            )
            for r in referrals
        ]
    )


@router.get("/leaderboard")
@limiter.limit("20/minute")
async def get_referral_leaderboard(
    request: Request,
    limit: int = 10,
    # Optional auth check - strictly speaking leaderboard can be public
    # but let's require at least a valid user or admin token?
    # For simplicity, we just rely on rate limiting if public, or use verify_user_access if needed.
    # User's verify_user_access requires an identifier in path which we don't have here.
    # So we'll leave it public but rate limited for now, or add a generic verify_token.
):
    """
    Get top referrers leaderboard.
    """
    referral_service = ReferralService()
    try:
        leaderboard = await referral_service.get_leaderboard(limit=limit)
        return {"leaderboard": leaderboard}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch leaderboard")


@router.get("/stats")
@limiter.limit("20/minute")
async def get_referral_stats(request: Request):
    """Get global referral statistics."""
    service = ReferralService()
    try:
        return await service.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch stats")


@router.get("/recent-bonuses")
@limiter.limit("20/minute")
async def get_recent_bonuses(request: Request, limit: int = 10):
    """Get recent bonus payouts."""
    service = ReferralService()
    try:
        bonuses = await service.get_recent_payouts(limit=limit)
        return {"bonuses": bonuses}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch bonuses")
