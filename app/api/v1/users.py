import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query, Header, Depends
from app.core.config import settings
from app.services.user_service import UserService
from app.repository.order_repo import OrderRepository
from app.repository.transaction_repo import TransactionRepository


logger = logging.getLogger(__name__)
router = APIRouter()


async def verify_admin_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """
    Verify the API key for admin-only endpoints.
    Uses SUPABASE_KEY as the admin API key for simplicity.
    """
    if x_api_key != settings.SUPABASE_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True


class WhatsAppUserRequest(BaseModel):
    phone_number: str
    name: Optional[str] = None
    referral_code: Optional[str] = None

@router.post("/ensure")
async def ensure_user(
    telegram_id: str,
    name: str = None,
    referral_code: str = None,
):
    """
    Ensure Telegram user exists, create if not.
    Can be called as POST with query params or JSON body.
    If referral_code is provided, register the referral.
    """
    user_service = UserService()
    
    if not telegram_id:
        raise HTTPException(status_code=400, detail="telegram_id is required")
    
    user, is_new_user = await user_service.get_or_create_telegram_user(
        telegram_id=telegram_id,
        name=name,
        referral_code=referral_code
    )
    
    return {
        "user_id": user["id"],
        "telegram_id": user.get("telegram_id"),
        "phone": user.get("phone"),
        "name": user.get("name"),
        "referral_code": user.get("referral_code"),
        "platform": user.get("platform"),
        "is_new_user": is_new_user
    }


@router.post("/ensure-whatsapp")
async def ensure_whatsapp_user(
    request: WhatsAppUserRequest
):
    """
    Ensure WhatsApp user exists, create if not.
    Uses phone number as identifier.
    If referral_code is provided, register the referral.
    """
    logger.info(f"Received WhatsApp user request: phone={request.phone_number}, name={request.name}")

    user_service = UserService()
    
    user, is_new_user = await user_service.get_or_create_whatsapp_user(
        phone_number=request.phone_number,
        name=request.name,
        referral_code=request.referral_code
    )
    
    return {
        "user_id": user["id"],
        "phone": user.get("phone"),
        "name": user.get("name"),
        "referral_code": user.get("referral_code"),
        "platform": user.get("platform"),
        "is_new_user": is_new_user
    }


@router.get("/{identifier}/history")
async def get_user_history(
    identifier: str,
    limit: int = Query(10, ge=1, le=100),
    identifier_type: str = Query("telegram_id", regex="^(telegram_id|phone)$")
):
    """
    Get transaction and order history for user.
    Can use either telegram_id or phone number as identifier.
    
    Args:
        identifier: User's telegram_id or phone number
        limit: Number of records to return (1-100)
        identifier_type: Type of identifier - "telegram_id" or "phone"
    """
    logger.info(f"Fetching history for identifier={identifier}, type={identifier_type}, limit={limit}")
    
    user_service = UserService()
    transaction_repo = TransactionRepository()
    order_repo = OrderRepository()
    
    # Get user by identifier type
    try:
        if identifier_type == "phone":
            user = await user_service.get_user_by_whatsapp_phone(identifier)
        else:
            user = await user_service.get_user_by_telegram_id(identifier)
    except Exception as e:
        logger.error(f"Error fetching user: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching user")
    
    if not user:
        logger.warning(f"User not found: identifier={identifier}, type={identifier_type}")
        raise HTTPException(status_code=404, detail="User not found")
    
    logger.info(f"Found user: user_id={user['id']}")
    
    # Get transactions
    try:
        transactions = await transaction_repo.get_by_user_id(user["id"], limit=limit)
        logger.info(f"Found {len(transactions)} transactions for user {user['id']}")
    except Exception as e:
        logger.error(f"Error fetching transactions: {str(e)}")
        transactions = []
    
    # Get orders
    try:
        orders = await order_repo.get_by_user_id(user["id"], limit=limit)
        logger.info(f"Found {len(orders)} orders for user {user['id']}")
    except Exception as e:
        logger.error(f"Error fetching orders: {str(e)}")
        orders = []

    return {
        "user_id": user["id"],
        "transactions": [
            {
                "id": t["id"],
                "type": t["type"],
                "amount": t["amount"],
                "currency": t["currency"],
                "status": t["status"],
                "reference": t["reference"],
                "created_at": t.get("created_at")
            }
            for t in transactions
        ],
        "orders": [
            {
                "id": o["id"],
                "bundle_id": o["bundle_id"],
                "phone": o["phone"],
                "price": o["price"],
                "status": o["status"],
                "vendor_reference": o.get("vendor_reference"),
                "created_at": o.get("created_at")
            }
            for o in orders
        ]
    }

@router.get("/{identifier}/debug-full")
async def debug_full_user_data(
    identifier: str,
    identifier_type: str = Query("telegram_id", regex="^(telegram_id|phone)$"),
    _: bool = Depends(verify_admin_api_key)  # Require API key authentication
):
    """
    Comprehensive debug endpoint to diagnose why transactions/orders aren't showing.
    """
    from app.db.supabase_client import supabase
    
    logger.info(f"FULL DEBUG: identifier={identifier}, type={identifier_type}")
    
    user_service = UserService()
    
    # Get user
    if identifier_type == "phone":
        user = await user_service.get_user_by_whatsapp_phone(identifier)
    else:
        user = await user_service.get_user_by_telegram_id(identifier)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_id = user["id"]
    logger.info(f"DEBUG: Found user_id={user_id}")
    
    
    # 1. Check base_users table
    base_user_check = await supabase.table("base_users").select("*").eq("id", user_id).execute()
    
    # 2. Check telegram_users table
    telegram_user_check = await supabase.table("telegram_users").select("*").eq("user_id", user_id).execute()
    
    # 3. Check whatsapp_users table
    whatsapp_user_check = await supabase.table("whatsapp_users").select("*").eq("user_id", user_id).execute()
    
    # 4. Get ALL transactions (no filter)
    all_transactions = await supabase.table("transactions").select("id, user_id, reference, amount, status").limit(100).execute()
    
    # 5. Get transactions for THIS user
    user_transactions = await supabase.table("transactions").select("*").eq("user_id", user_id).execute()
    
    # 6. Get ALL orders (no filter)
    all_orders = await supabase.table("orders").select("id, user_id, phone, price, status").limit(100).execute()
    
    # 7. Get orders for THIS user
    user_orders = await supabase.table("orders").select("*").eq("user_id", user_id).execute()
    
    # 8. Check if there are transactions/orders with telegram_id instead of user_id
    transactions_with_telegram_id = []
    if user.get("telegram_id"):
        # This will fail if telegram_id is not a valid UUID, but let's try
        try:
            telegram_id_as_uuid_check = await supabase.table("transactions").select("*").eq("user_id", user["telegram_id"]).execute()
            transactions_with_telegram_id = telegram_id_as_uuid_check.data or []
        except Exception as query_error:
            logger.warning(f"Failed to query transactions with telegram_id: {query_error}")
            transactions_with_telegram_id = []
    
    orders_with_telegram_id = []
    if user.get("telegram_id"):
        try:
            telegram_id_as_uuid_check = await supabase.table("orders").select("*").eq("user_id", user["telegram_id"]).execute()
            orders_with_telegram_id = telegram_id_as_uuid_check.data or []
        except Exception as query_error:
            logger.warning(f"Failed to query orders with telegram_id: {query_error}")
            orders_with_telegram_id = []
    
    # 9. Sample unique user_ids from transactions and orders
    transaction_user_ids = set(t["user_id"] for t in all_transactions.data if t.get("user_id"))
    order_user_ids = set(o["user_id"] for o in all_orders.data if o.get("user_id"))
    
    # 10. Check if any of those user_ids match any telegram_id or phone in the system
    mismatched_user_ids = []
    for uid in list(transaction_user_ids | order_user_ids)[:10]:  # Check first 10
        # Check if this uid exists in base_users
        check = await supabase.table("base_users").select("id").eq("id", uid).execute()
        if not check.data:
            mismatched_user_ids.append({
                "user_id": uid,
                "exists_in_base_users": False
            })
    
    return {
        "query_info": {
            "identifier": identifier,
            "identifier_type": identifier_type,
            "resolved_user_id": user_id
        },
        "user_data": {
            "id": user_id,
            "telegram_id": user.get("telegram_id"),
            "phone": user.get("phone"),
            "name": user.get("name"),
            "platform": user.get("platform")
        },
        "table_checks": {
            "exists_in_base_users": len(base_user_check.data) > 0,
            "exists_in_telegram_users": len(telegram_user_check.data) > 0,
            "exists_in_whatsapp_users": len(whatsapp_user_check.data) > 0
        },
        "stats": {
            "total_transactions_in_db": len(all_transactions.data),
            "transactions_for_this_user_id": len(user_transactions.data),
            "total_orders_in_db": len(all_orders.data),
            "orders_for_this_user_id": len(user_orders.data),
            "transactions_with_telegram_id_as_user_id": len(transactions_with_telegram_id),
            "orders_with_telegram_id_as_user_id": len(orders_with_telegram_id)
        },
        "unique_user_ids": {
            "in_transactions": list(transaction_user_ids)[:10],
            "in_orders": list(order_user_ids)[:10],
            "mismatched_user_ids": mismatched_user_ids
        },
        "sample_data": {
            "sample_transactions": [
                {
                    "id": t.get("id"),
                    "user_id": t.get("user_id"),
                    "reference": t.get("reference"),
                    "amount": t.get("amount"),
                    "status": t.get("status")
                }
                for t in all_transactions.data[:5]
            ],
            "sample_orders": [
                {
                    "id": o.get("id"),
                    "user_id": o.get("user_id"),
                    "phone": o.get("phone"),
                    "price": o.get("price"),
                    "status": o.get("status")
                }
                for o in all_orders.data[:5]
            ],
            "this_user_transactions": user_transactions.data[:5],
            "this_user_orders": user_orders.data[:5]
        }
    }