from app.models.user import User
from app.db.session import get_db
from app.models.order import Order
from sqlalchemy import select, desc
from app.models.transaction import Transaction
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException
from app.services.referral_service import ReferralService

router = APIRouter()


@router.post("/ensure")
async def ensure_user(
    telegram_id: str,
    name: str = None,
    referral_code: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Ensure user exists, create if not.
    Can be called as POST with query params or JSON body.
    If referral_code is provided, register the referral.
    """
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    is_new_user = False
    if not user:
        is_new_user = True
        user = User(telegram_id=telegram_id, name=name)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Generate referral code for new user
        await ReferralService.get_or_create_referral_code(db, user.id)
        
        # Register referral if code was provided
        if referral_code:
            await ReferralService.register_referral(db, user.id, referral_code)
        
        await db.refresh(user)
    elif name and user.name != name:
        user.name = name
        await db.commit()
        await db.refresh(user)
    
    return {
        "user_id": str(user.id),
        "telegram_id": user.telegram_id,
        "name": user.name,
        "referral_code": user.referral_code,
        "is_new_user": is_new_user
    }


@router.get("/{telegram_id}/history")
async def get_user_history(
    telegram_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Get transaction and order history for user.
    """
    # Get user
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get transactions
    transactions_stmt = (
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(desc(Transaction.created_at))
        .limit(limit)
    )
    transactions_result = await db.execute(transactions_stmt)
    transactions = transactions_result.scalars().all()
    
    # Get orders
    orders_stmt = (
        select(Order)
        .where(Order.user_id == user.id)
        .order_by(desc(Order.created_at))
        .limit(limit)
    )
    orders_result = await db.execute(orders_stmt)
    orders = orders_result.scalars().all()
    
    return {
        "transactions": [
            {
                "id": str(t.id),
                "type": t.type.value,
                "amount": str(t.amount),
                "currency": t.currency,
                "status": t.status.value,
                "reference": t.reference,
                "created_at": t.created_at.isoformat() if t.created_at else None
            }
            for t in transactions
        ],
        "orders": [
            {
                "id": str(o.id),
                "bundle_id": str(o.bundle_id),
                "phone": o.phone,
                "price": str(o.price),
                "status": o.status.value,
                "vendor_reference": o.vendor_reference,
                "created_at": o.created_at.isoformat() if o.created_at else None
            }
            for o in orders
        ]
    }

