"""Order API endpoints using Supabase repositories."""
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from app.services.order_service import OrderService
from app.services.user_service import UserService

router = APIRouter()


class CreateOrderRequest(BaseModel):
    telegram_id: Optional[str] = None  # Optional, for Telegram users
    user_id: Optional[str] = None  # Optional, for WhatsApp users (can pass user_id directly)
    bundle_id: str
    phone: str


@router.post("")
async def create_order(request: CreateOrderRequest):
    """
    Create a bundle purchase order.
    """
    
    user_service = UserService()
    
    # Get user - either by user_id (WhatsApp) or telegram_id (Telegram)
    if request.user_id:
        # WhatsApp: user_id provided directly
        user = await user_service.get_user_by_id(request.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    elif request.telegram_id:
        # Telegram: look up by telegram_id
        user = await user_service.get_user_by_telegram_id(request.telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    else:
        raise HTTPException(status_code=400, detail="Either telegram_id or user_id must be provided")
    
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
            "order": order,
            "order_id": order["id"],
            "order_status": order["status"],
            "vendor_reference": order.get("vendor_reference")
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
