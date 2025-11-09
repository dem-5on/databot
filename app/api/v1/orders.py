"""Order API endpoints using Supabase repositories."""
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from app.repository.user_repo import UserRepository
from app.services.order_service import OrderService

router = APIRouter()


class CreateOrderRequest(BaseModel):
    telegram_id: str
    bundle_id: str
    phone: str


@router.post("")
async def create_order(request: CreateOrderRequest):
    """
    Create a bundle purchase order.
    """
    user_repo = UserRepository()
    
    # Get user
    user = user_repo.get_by_telegram_id(request.telegram_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create order
    order_service = OrderService()
    try:
        order = await order_service.create_order(
            user_id=user["id"],
            bundle_id=request.bundle_id,
            phone=request.phone
        )
        
        return {
            "status": "success",
            "order_id": order["id"],
            "order_status": order["status"],
            "vendor_reference": order.get("vendor_reference")
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
