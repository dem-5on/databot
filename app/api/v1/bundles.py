from typing import Optional
from sqlalchemy import select
from app.db.session import get_db
from app.models.bundle import Bundle
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.bundle_sync import BundleSyncService

router = APIRouter()


@router.get("")
async def get_bundles(
    network: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get available bundles, optionally filtered by network.
    """
    if network:
        stmt = select(Bundle).where(
            Bundle.network == network.upper(),
            Bundle.active == True
        ).order_by(Bundle.price)
    else:
        stmt = select(Bundle).where(
            Bundle.active == True
        ).order_by(Bundle.price)
    
    result = await db.execute(stmt)
    bundles = result.scalars().all()
    
    return {
        "bundles": [
            {
                "id": str(b.id),
                "network": b.network,
                "capacity": b.capacity,
                "mb": b.mb,
                "price": str(b.price),
                "currency": b.currency
            }
            for b in bundles
        ]
    }

