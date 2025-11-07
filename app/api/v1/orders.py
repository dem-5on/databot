from uuid import UUID
from sqlalchemy import select
from pydantic import BaseModel
from app.models.user import User
from app.db.session import get_db
from app.models.order import Order
from app.models.transaction import Transaction
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.order_service import OrderService
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()


class CreateOrderRequest(BaseModel):
    telegram_id: str
    bundle_id: str
    phone: str


@router.post("")
async def create_order(
    request: CreateOrderRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a bundle purchase order.
    """
    # Get user
    stmt = select(User).where(User.telegram_id == request.telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Parse bundle_id
    try:
        bundle_id = UUID(request.bundle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid bundle_id format")
    
    # Create order
    order_service = OrderService()
    try:
        order = await order_service.create_order(
            db=db,
            user_id=str(user.id),
            bundle_id=str(bundle_id),
            phone=request.phone
        )
        
        return {
            "status": "success",
            "order_id": str(order.id),
            "order_status": order.status.value,
            "vendor_reference": order.vendor_reference
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

