"""Order API endpoints using Supabase repositories."""
import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends, Request
from app.services.order_service import OrderService
from app.services.user_service import UserService
from app.core.auth import get_user_identity, UserIdentity
from app.core.rate_limit import limiter
from app.utils.security_utils import validate_uuid_format, safe_error_response

logger = logging.getLogger(__name__)
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
    
    logger.info(f"Order request: user_id={request.user_id}, telegram_id={request.telegram_id}, bundle_id={request.bundle_id}, phone={request.phone}")
    logger.info(f"Auth user: user_id={user.user_id}, platform={user.platform}")

    # SECURITY: Validate bundle_id is a valid UUID format
    try:
        validate_uuid_format(request.bundle_id, "Bundle ID")
    except ValueError as e:
        logger.error(f"Invalid bundle_id format: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    user_service = UserService()
    
    # Get user - either by user_id (WhatsApp) or telegram_id (Telegram)
    if request.user_id:
        logger.info(f"Looking up user by user_id: {request.user_id}")
        # For WhatsApp: user authenticates with phone number but passes database UUID
        # We need to verify the UUID belongs to the authenticated phone number
        db_user = await user_service.get_user_by_id(request.user_id)
        if not db_user:
            logger.error(f"User not found for user_id: {request.user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        
        # SECURITY: Verify the authenticated user owns this user_id
        # For WhatsApp, X-User-ID is the phone number, so we check against the db user's phone
        if user.platform == "whatsapp":
            logger.info(f"WhatsApp auth: looking up user by phone {user.user_id}")
            # Get the WhatsApp phone associated with this user
            whatsapp_user = await user_service.get_user_by_whatsapp_phone(user.user_id)
            logger.info(f"WhatsApp user found: {whatsapp_user['id'] if whatsapp_user else None}")
            if not whatsapp_user or whatsapp_user["id"] != request.user_id:
                logger.error(f"User ID mismatch: whatsapp_user_id={whatsapp_user['id'] if whatsapp_user else None}, request.user_id={request.user_id}")
                raise HTTPException(status_code=403, detail="User ID mismatch")
        else:
            # For Telegram, the user_id should match directly
            if request.user_id != user.user_id:
                raise HTTPException(status_code=403, detail="User ID mismatch")
                
    elif request.telegram_id:
        logger.info(f"Looking up user by telegram_id: {request.telegram_id}")
        # SECURITY: Validate telegram_id matches authenticated user
        if request.telegram_id != user.user_id:
            raise HTTPException(status_code=403, detail="Telegram ID mismatch")
        db_user = await user_service.get_user_by_telegram_id(request.telegram_id)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
    else:
        logger.error("Neither telegram_id nor user_id provided")
        raise HTTPException(status_code=400, detail="Either telegram_id or user_id must be provided")
    
    logger.info(f"Creating order for db_user: {db_user['id']}")
    
    # Create order
    order_service = OrderService()
    try:
        order = await order_service.create_order(
            user_id=db_user["id"],
            bundle_id=request.bundle_id,
            phone=request.phone
        )
        
        logger.info(f"Order created successfully: {order['id']}")
        return {
            "status": "success",
            "order": order,
            "order_id": order["id"],
            "order_status": order["status"],
            "vendor_reference": order.get("vendor_reference")
        }
    except ValueError as e:
        logger.error(f"ValueError in order creation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Exception in order creation: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=safe_error_response(e, "creating order"))
