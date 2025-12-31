"""Order API endpoints using Supabase repositories."""
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends, Request
from app.services.order_service import OrderService
from app.services.user_service import UserService
from app.core.auth import get_user_identity, UserIdentity
from app.core.rate_limit import limiter
from app.utils.security_utils import validate_uuid_format, safe_error_response

router = APIRouter()


class CreateOrderRequest(BaseModel):
    telegram_id: Optional[str] = None  # Optional, for Telegram users
    user_id: Optional[str] = None  # Optional, for WhatsApp users (can pass user_id directly)
    bundle_id: str
    phone: str


@router.post("")
@limiter.limit("5/minute")
async def create_order(
    request: Request,
    order_in: CreateOrderRequest,
    user: UserIdentity = Depends(get_user_identity)
):
    """
    Create a bundle purchase order.
    """
    # Use request data renamed to avoid conflict with Request object
    request = order_in

    # SECURITY: Validate bundle_id is a valid UUID format
    try:
        validate_uuid_format(request.bundle_id, "Bundle ID")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    user_service = UserService()
    
    # Get user - either by user_id (WhatsApp) or telegram_id (Telegram)
    if request.user_id:
        # SECURITY: Validate user_id matches authenticated user
        if request.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="User ID mismatch")
        db_user = await user_service.get_user_by_id(request.user_id)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
    elif request.telegram_id:
        # SECURITY: Validate telegram_id matches authenticated user
        if request.telegram_id != user.user_id:
            raise HTTPException(status_code=403, detail="Telegram ID mismatch")
        db_user = await user_service.get_user_by_telegram_id(request.telegram_id)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
    else:
        raise HTTPException(status_code=400, detail="Either telegram_id or user_id must be provided")
    
    # Create order
    order_service = OrderService()
    try:
        order = await order_service.create_order(
            user_id=db_user["id"],
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
        raise HTTPException(status_code=500, detail=safe_error_response(e, "creating order"))
