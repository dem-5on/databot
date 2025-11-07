from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.services.referral_service import ReferralService

router = APIRouter()


@router.get("/code/{telegram_id}")
async def get_referral_code(
    telegram_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get user's referral code."""
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get or create referral code
    referral_code = await ReferralService.get_or_create_referral_code(db, user.id)
    
    return {
        "telegram_id": telegram_id,
        "referral_code": referral_code,
        "referral_link": f"https://t.me/your_bot_username?start={referral_code}"
    }


@router.get("/referrals/{telegram_id}")
async def get_referrals(
    telegram_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get list of users referred by this user."""
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    referrals = await ReferralService.get_user_referrals(db, user.id)
    
    return {
        "telegram_id": telegram_id,
        "total_referrals": len(referrals),
        "referrals": referrals
    }

