import asyncio
import logging
from typing import Optional, List
from decimal import Decimal
from app.core.config import settings
from datetime import datetime, timedelta
from app.core.auth import verify_dashboard_token
from app.services.order_service import OrderService
from app.repository.order_repo import OrderRepository
from app.repository.bundle_repo import BundleRepository
from app.repository.wallet_repo import WalletRepository
from fastapi import APIRouter, HTTPException, Depends, Query
from app.tasks import broadcast_telegram, broadcast_whatsapp
from app.repository.base_user_repo import BaseUserRepository
from app.repository.transaction_repo import TransactionRepository
from app.repository.telegram_user_repo import TelegramUserRepository
from app.repository.whatsapp_user_repo import WhatsAppUserRepository
from app.utils.security_utils import safe_error_response, validate_uuid_format

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(_: str = Depends(verify_dashboard_token)):
    """
    Get overview statistics for the dashboard.
    """
    user_repo = BaseUserRepository()
    transaction_repo = TransactionRepository()
    order_repo = OrderRepository()
    
    try:
        # Get total counts
        total_users = await user_repo.count()
        
        # Get successful deposits (revenue)
        all_deposits = await transaction_repo.get_all_by_field("type", "deposit")
        successful_deposits = [t for t in all_deposits if t["status"] == "success" or t["status"] == "completed"]
        
        total_revenue = sum(float(t["amount"]) for t in successful_deposits)
        
        # Get today's stats
        today = datetime.utcnow().date()
        today_iso = today.isoformat()
        
        today_deposits = [
            t for t in successful_deposits 
            if t["created_at"].startswith(today_iso)
        ]
        today_revenue = sum(float(t["amount"]) for t in today_deposits)
        
        # Get orders stats
        all_orders = await order_repo.get_all(limit=1000)
        pending_orders = len([o for o in all_orders if o["status"] == "pending" or o["status"] == "processing"])
        failed_orders = len([o for o in all_orders if o["status"] == "failed"])
        completed_orders = len([o for o in all_orders if o["status"] == "completed" or o["status"] == "success"])
        
        return {
            "users": {
                "total": total_users,
            },
            "revenue": {
                "total": round(total_revenue, 2),
                "today": round(today_revenue, 2),
                "currency": "GHS"
            },
            "orders": {
                "pending": pending_orders,
                "failed": failed_orders,
                "completed": completed_orders,
                "total": len(all_orders)
            },
            "system_health": "healthy"
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stats")


@router.get("/users")
async def list_dashboard_users(
    limit: int = Query(50, ge=1, le=100),
    offset: int = 0,
    search: Optional[str] = None,
    platform: Optional[str] = None,
    _: str = Depends(verify_dashboard_token)
):
    """
    List users with optional search and platform filter.
    """
    user_repo = BaseUserRepository()
    wallet_repo = WalletRepository()
    telegram_repo = TelegramUserRepository()
    whatsapp_repo = WhatsAppUserRepository()
    
    try:
        # Parallel fetch for performance
        users, telegram_users, whatsapp_users, wallets = await asyncio.gather(
            user_repo.get_all(limit=1000, order_by="created_at", ascending=False),
            telegram_repo.get_all(limit=1000),
            whatsapp_repo.get_all(limit=1000),
            wallet_repo.get_all(limit=1000)
        )
        
        # Create lookup maps by user_id
        telegram_map = {t.get("user_id"): t for t in telegram_users if t.get("user_id")}
        whatsapp_map = {w.get("user_id"): w for w in whatsapp_users if w.get("user_id")}
        wallet_map = {w.get("user_id"): w for w in wallets if w.get("user_id")}
        
        # Enrich users with platform data
        enriched_users = []
        for user in users:
            user_id = user.get("id")
            
            telegram_data = telegram_map.get(user_id)
            whatsapp_data = whatsapp_map.get(user_id)
            
            # Determine platform
            if telegram_data:
                user_platform = "telegram"
                identifier = telegram_data.get("telegram_id") or telegram_data.get("phone")
            elif whatsapp_data:
                user_platform = "whatsapp"
                identifier = whatsapp_data.get("phone")
            else:
                user_platform = "unknown"
                identifier = None
            
            wallet_data = wallet_map.get(user_id)
            balance = wallet_data.get("balance", "0.00") if wallet_data else "0.00"
            
            enriched_user = {
                **user,
                "platform": user_platform,
                "telegram_id": telegram_data.get("telegram_id") if telegram_data else None,
                "phone": whatsapp_data.get("phone") if whatsapp_data else (telegram_data.get("phone") if telegram_data else None),
                "identifier": identifier,
                "balance": balance,
            }
            enriched_users.append(enriched_user)
        
        # Apply platform filter
        filtered_users = enriched_users
        if platform:
            filtered_users = [u for u in filtered_users if u.get("platform") == platform]
        
        # Apply search filter
        if search:
            search = search.lower()
            filtered_users = [
                u for u in filtered_users 
                if (u.get("name") and search in u.get("name").lower()) or 
                   (u.get("phone") and search in u.get("phone")) or
                   (u.get("telegram_id") and search in str(u.get("telegram_id"))) or
                   (u.get("identifier") and search in str(u.get("identifier")))
            ]
        
        # Apply pagination
        total = len(filtered_users)
        paginated_users = filtered_users[offset : offset + limit]
        
        return {
            "total": total,
            "users": paginated_users,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error listing users for dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to list users")


@router.get("/transactions")
async def list_dashboard_transactions(
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    type: Optional[str] = None,
    _: str = Depends(verify_dashboard_token)
):
    """
    List recent transactions with user identifiers.
    """
    transaction_repo = TransactionRepository()
    telegram_repo = TelegramUserRepository()
    whatsapp_repo = WhatsAppUserRepository()
    
    try:
        # Build query
        query = transaction_repo.client.table(transaction_repo.table_name).select("*")
        
        if status:
            query = query.eq("status", status)
        if type:
            query = query.eq("type", type)
            
        response = await query.order("created_at", desc=True).limit(limit).execute()
        transactions = response.data if response.data else []
        
        # Parallel fetch for performance
        telegram_users, whatsapp_users = await asyncio.gather(
            telegram_repo.get_all(limit=1000),
            whatsapp_repo.get_all(limit=1000)
        )
        
        # Create lookup maps
        telegram_map = {t.get("user_id"): t for t in telegram_users if t.get("user_id")}
        whatsapp_map = {w.get("user_id"): w for w in whatsapp_users if w.get("user_id")}
        
        # Enrich transactions with user info
        enriched_transactions = []
        for tx in transactions:
            user_id = tx.get("user_id")
            
            telegram_data = telegram_map.get(user_id)
            whatsapp_data = whatsapp_map.get(user_id)
            
            if telegram_data:
                user_identifier = telegram_data.get("telegram_id") or telegram_data.get("phone")
                user_platform = "telegram"
            elif whatsapp_data:
                user_identifier = whatsapp_data.get("phone")
                user_platform = "whatsapp"
            else:
                user_identifier = user_id[:8] + "..." if user_id else "Unknown"
                user_platform = "unknown"
            
            enriched_tx = {
                **tx,
                "user_identifier": user_identifier,
                "user_platform": user_platform,
            }
            enriched_transactions.append(enriched_tx)
        
        return {
            "transactions": enriched_transactions
        }
    except Exception as e:
        logger.error(f"Error listing transactions for dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to list transactions")


@router.get("/orders")
async def list_dashboard_orders(
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    _: str = Depends(verify_dashboard_token)
):
    """
    List recent orders.
    """
    order_repo = OrderRepository()
    try:
        query = order_repo.client.table(order_repo.table_name).select("*")
        if status:
            if status.lower() == "processing":
                # Include orders that are pending processing OR pending delivery
                # Exclude failed orders
                query = query.eq("delivery_status", "pending").neq("status", "failed")
            else:
                query = query.eq("status", status)
            
        response = await query.order("created_at", desc=True).limit(limit).execute()
        return {
            "orders": response.data if response.data else []
        }
    except Exception as e:
        logger.error(f"Error listing orders for dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to list orders")


@router.get("/bundles")
async def list_dashboard_bundles(_: str = Depends(verify_dashboard_token)):
    """
    List all bundles with their cost prices and status.
    """
    bundle_repo = BundleRepository()
    try:
        bundles = await bundle_repo.get_all(order_by="network")
        
        # Sort bundles by capacity within each network (smallest to largest)
        def parse_capacity(capacity_str: str) -> float:
            """Parse capacity string like '1GB', '500MB' to numeric value in GB."""
            try:
                cap = str(capacity_str).upper().strip()
                if "GB" in cap:
                    return float(cap.replace("GB", "").strip())
                elif "MB" in cap:
                    return float(cap.replace("MB", "").strip()) / 1024
                else:
                    return float(cap)
            except Exception:
                return 0.0
        
        # Sort by network first, then by capacity
        bundles = sorted(bundles, key=lambda b: (b.get("network", ""), parse_capacity(b.get("capacity", "0"))))
        
        return {"bundles": bundles}
    except Exception as e:
        logger.error(f"Error listing bundles for dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to list bundles")


@router.patch("/bundles/{bundle_id}")
async def update_bundle(
    bundle_id: str,
    active: Optional[bool] = None,
    capacity: Optional[str] = None,
    price: Optional[float] = None,
    mb: Optional[str] = None,
    _: str = Depends(verify_dashboard_token)
):
    """
    Update a bundle's properties (active status, capacity, price, etc).
    """
    bundle_repo = BundleRepository()
    try:
        # First check if bundle exists
        existing = await bundle_repo.get_by_id(bundle_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Bundle not found")
        
        update_data = {}
        if active is not None:
            update_data["active"] = active
        if capacity is not None:
            update_data["capacity"] = capacity
        if price is not None:
            update_data["price"] = str(price)
        if mb is not None:
            update_data["mb"] = mb
            
        if not update_data:
            raise HTTPException(status_code=400, detail="No update fields provided")
        
        # If capacity is being changed, check for duplicates
        if capacity and capacity != existing.get("capacity"):
            network = existing.get("network")
            # Check if this network+capacity combo already exists
            existing_bundles = await bundle_repo.get_by_network(network, active_only=False)
            for b in existing_bundles:
                if b.get("capacity") == capacity and b.get("id") != bundle_id:
                    raise HTTPException(
                        status_code=409, 
                        detail=f"A {network} bundle with capacity '{capacity}' already exists"
                    )
            
        updated = await bundle_repo.update(bundle_id, update_data)
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update bundle - database error")
        return {"status": "success", "bundle": updated}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "duplicate key" in error_msg or "unique constraint" in error_msg:
            raise HTTPException(status_code=409, detail="A bundle with this capacity already exists for this network")
        logger.error(f"Error updating bundle {bundle_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update bundle: {error_msg}")


@router.post("/bundles")
async def create_bundle(
    network: str,
    capacity: str,
    price: float,
    mb: Optional[str] = None,
    currency: str = "GHS",
    active: bool = True,
    _: str = Depends(verify_dashboard_token)
):
    """
    Create a new bundle.
    """
    bundle_repo = BundleRepository()
    
    # Normalize network name to uppercase for consistency
    NETWORK_MAP = {
        "mtn": "MTN",
        "vodafone": "VODAFONE", 
        "airteltigo": "AIRTELTIGO",
        "airtel-tigo": "AIRTELTIGO",
    }
    normalized_network = NETWORK_MAP.get(network.lower(), network.upper())
    
    try:
        # Check if bundle already exists
        existing_bundles = await bundle_repo.get_by_network(normalized_network, active_only=False)
        for b in existing_bundles:
            if b.get("capacity") == capacity:
                raise HTTPException(
                    status_code=409, 
                    detail=f"A {normalized_network} bundle with capacity '{capacity}' already exists"
                )
        
        # Create new bundle
        bundle = await bundle_repo.upsert_bundle(
            network=normalized_network,
            capacity=capacity,
            mb=mb or capacity,
            price=Decimal(str(price)),
            currency=currency,
            active=active
        )
        if not bundle:
            raise HTTPException(status_code=500, detail="Failed to create bundle")
        return {"status": "success", "bundle": bundle}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "duplicate key" in error_msg or "unique constraint" in error_msg:
            raise HTTPException(status_code=409, detail="A bundle with this capacity already exists for this network")
        logger.error(f"Error creating bundle: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create bundle: {error_msg}")


@router.delete("/bundles/{bundle_id}")
async def delete_bundle(
    bundle_id: str,
    _: str = Depends(verify_dashboard_token)
):
    """
    Delete a bundle.
    """
    bundle_repo = BundleRepository()
    try:
        success = await bundle_repo.delete_by_id(bundle_id)
        if not success:
            raise HTTPException(status_code=404, detail="Bundle not found")
        return {"status": "success", "message": "Bundle deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting bundle {bundle_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete bundle: {str(e)}")


@router.post("/users/{user_id}/credit")
async def manual_credit_user(
    user_id: str,
    amount: float,
    reason: str,
    _: str = Depends(verify_dashboard_token)
):
    """
    Manually credit a user's wallet.
    
    Business Logic Limits:
    - Maximum single credit amount enforced via MAX_MANUAL_CREDIT_AMOUNT
    - User must exist before crediting
    - Reason is required for audit trail
    """
    # SECURITY: Validate amount limits to prevent business logic abuse
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    max_amount = getattr(settings, 'MAX_MANUAL_CREDIT_AMOUNT', 10000.0)
    if amount > max_amount:
        raise HTTPException(
            status_code=400, 
            detail=f"Amount exceeds maximum allowed credit of GHS {max_amount}"
        )
    
    # Validate reason is provided
    if not reason or len(reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="A valid reason (min 5 chars) is required for audit")
    
    # SECURITY: Validate user_id format (prevent injection)
    try:
        validate_uuid_format(user_id, "User ID")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # SECURITY: Verify user exists before crediting
    user_repo = BaseUserRepository()
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        transaction_repo = TransactionRepository()
        import uuid
        
        reference = f"MAN-{uuid.uuid4().hex[:8].upper()}"
        
        # Create transaction with audit info
        await transaction_repo.create_transaction(
            user_id=user_id,
            transaction_type="deposit",
            amount=Decimal(str(amount)),
            currency="GHS",
            reference=reference,
            status="completed",
            provider="admin_manual",
            raw_payload={
                "reason": reason.strip(), 
                "type": "manual_credit",
                "credited_at": datetime.utcnow().isoformat()
            }
        )
        
        # Update wallet balance - use direct credit without reference check
        # since we just created the transaction
        wallet_repo = WalletRepository()
        wallet = await wallet_repo.get_or_create_wallet(user_id)
        new_wallet = await wallet_repo.credit_balance(wallet["id"], Decimal(str(amount)))
        
        logger.info(f"Manual credit: user={user_id}, amount={amount}, reason={reason[:50]}")
        
        return {
            "status": "success", 
            "message": f"Successfully credited GHS {amount}",
            "wallet": new_wallet
        }
    except Exception as e:
        logger.error(f"Error manually crediting user: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=safe_error_response(e, "crediting user"))


@router.get("/revenue-chart")
async def get_revenue_chart_data(_: str = Depends(verify_dashboard_token)):
    """
    Get revenue data for the last 7 days for chart display.
    """
    transaction_repo = TransactionRepository()
    
    try:
        # Get all successful deposits
        all_deposits = await transaction_repo.get_all_by_field("type", "deposit")
        successful_deposits = [
            t for t in all_deposits 
            if t["status"] == "success" or t["status"] == "completed"
        ]
                
        today = datetime.utcnow().date()
        days = []
        
        for i in range(6, -1, -1):  # Last 7 days, oldest first
            day = today - timedelta(days=i)
            day_str = day.isoformat()
            day_name = day.strftime("%a")  # Mon, Tue, etc.
            
            day_deposits = [
                t for t in successful_deposits
                if t["created_at"].startswith(day_str)
            ]
            
            day_revenue = sum(float(t["amount"]) for t in day_deposits)
            day_orders = len(day_deposits)
            
            days.append({
                "name": day_name,
                "date": day_str,
                "revenue": round(day_revenue, 2),
                "orders": day_orders
            })
        
        return {"data": days}
    except Exception as e:
        logger.error(f"Error fetching revenue chart data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chart data")


@router.get("/order-distribution")
async def get_order_distribution(_: str = Depends(verify_dashboard_token)):
    """
    Get order distribution by network for pie/donut chart.
    """
    order_repo = OrderRepository()
    bundle_repo = BundleRepository()
    
    try:
        # Get all orders
        all_orders = await order_repo.get_all(limit=1000)
        
        # Get all bundles to map bundle_id -> network
        all_bundles = await bundle_repo.get_all(limit=500)
        bundle_network_map = {b["id"]: b.get("network", "Unknown") for b in all_bundles}
        
        # Count by network
        distribution = {}
        for order in all_orders:
            bundle_id = order.get("bundle_id")
            network = bundle_network_map.get(bundle_id, "Unknown")
            distribution[network] = distribution.get(network, 0) + 1
        
        # Format for chart
        result = [
            {"network": network, "count": count, "percentage": 0}
            for network, count in distribution.items()
        ]
        
        # Calculate percentages
        total = sum(item["count"] for item in result)
        if total > 0:
            for item in result:
                item["percentage"] = round((item["count"] / total) * 100, 1)
        
        return {"distribution": result, "total": total}
    except Exception as e:
        logger.error(f"Error fetching order distribution: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch distribution data")


@router.get("/recent-activity")
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=50),
    _: str = Depends(verify_dashboard_token)
):
    """
    Get recent activity feed combining transactions, orders, and new users.
    """
    transaction_repo = TransactionRepository()
    order_repo = OrderRepository()
    
    try:
        activities = []
        
        # Get recent transactions
        recent_transactions = await transaction_repo.get_all(limit=20, order_by="created_at", ascending=False)
        for tx in recent_transactions[:10]:
            activity_type = "deposit"
            status = tx.get("status", "pending")
            amount = tx.get("amount", 0)
            
            if status == "success" or status == "completed":
                message = f"GHS {amount} deposit confirmed"
            elif status == "pending":
                message = f"GHS {amount} deposit pending"
            else:
                message = f"GHS {amount} deposit {status}"
            
            activities.append({
                "id": f"tx-{tx['id']}",
                "type": activity_type,
                "message": message,
                "created_at": tx.get("created_at"),
            })
        
        # Get recent orders
        recent_orders = await order_repo.get_all(limit=20, order_by="created_at", ascending=False)
        for order in recent_orders[:10]:
            status = order.get("status", "processing")
            
            if status == "completed" or status == "success":
                message = "Bundle order completed"
            elif status == "processing" or status == "pending":
                message = "Bundle order processing"
            else:
                message = f"Bundle order {status}"
            
            activities.append({
                "id": f"order-{order['id']}",
                "type": "order",
                "message": message,
                "created_at": order.get("created_at"),
            })
        
        telegram_repo = TelegramUserRepository()
        whatsapp_repo = WhatsAppUserRepository()
        
        recent_tg = await telegram_repo.get_all(limit=5, order_by="created_at", ascending=False)
        for user in recent_tg:
            name = user.get('name') or user.get('telegram_id')
            activities.append({
                "id": f"user-tg-{user['id']}",
                "type": "user",
                "message": f"New user joined via Telegram ({name})",
                "created_at": user.get("created_at"),
            })
            
        recent_wa = await whatsapp_repo.get_all(limit=5, order_by="created_at", ascending=False)
        for user in recent_wa:
            phone = user.get('phone', 'Unknown')
            activities.append({
                "id": f"user-wa-{user['id']}",
                "type": "user",
                "message": f"New user joined via WhatsApp ({phone})",
                "created_at": user.get("created_at"),
            })
        
        # Sort all activities by created_at and limit
        activities.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        activities = activities[:limit]
                
        now = datetime.utcnow()
        
        for activity in activities:
            created_at = activity.get("created_at")
            if created_at:
                try:
                    # Parse ISO datetime
                    if "T" in created_at:
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00").replace("+00:00", ""))
                    else:
                        dt = datetime.fromisoformat(created_at)
                    
                    diff = now - dt
                    minutes = int(diff.total_seconds() / 60)
                    
                    if minutes < 1:
                        activity["time"] = "Just now"
                    elif minutes < 60:
                        activity["time"] = f"{minutes} min ago"
                    elif minutes < 1440:
                        hours = minutes // 60
                        activity["time"] = f"{hours} hour{'s' if hours > 1 else ''} ago"
                    else:
                        days = minutes // 1440
                        activity["time"] = f"{days} day{'s' if days > 1 else ''} ago"
                except Exception:
                    activity["time"] = "Unknown"
            else:
                activity["time"] = "Unknown"
        
        return {"activities": activities}
    except Exception as e:
        logger.error(f"Error fetching recent activity: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch activity")


@router.get("/user-growth-chart")
async def get_user_growth_chart(_: str = Depends(verify_dashboard_token)):
    """
    Get user growth data for the last 30 days.
    """
    user_repo = BaseUserRepository()
    
    try:
        # Get all users (limit might need to be increased if > 1000 users)
        all_users = await user_repo.get_all(limit=5000)
        
        # Group by day for the last 30 days
        today = datetime.utcnow().date()
        days_map = {}
        
        # Initialize last 30 days with 0
        for i in range(29, -1, -1):
            day = today - timedelta(days=i)
            day_str = day.isoformat()
            days_map[day_str] = 0
            
        # Count users per day
        for user in all_users:
            created_at = user.get("created_at")
            if created_at:
                # Extract YYYY-MM-DD
                day_str = created_at.split("T")[0]
                if day_str in days_map:
                    days_map[day_str] += 1
        
        # Convert to list
        chart_data = [
            {"date": day, "count": count}
            for day, count in days_map.items()
        ]
        
        # Sort by date
        chart_data.sort(key=lambda x: x["date"])
        
        # Calculate cumulative if needed, or just daily new users
        # Let's do cumulative
        cumulative = 0
        result = []
        for item in chart_data:
            cumulative += item["count"]
            result.append({
                "date": item["date"],
                "new_users": item["count"],
                "total_users": cumulative
            })
            
        return {"data": result}
    except Exception as e:
        logger.error(f"Error fetching user growth chart: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chart data")


@router.post("/orders/{order_id}/sync")
async def sync_order_status_endpoint(
    order_id: str,
    _: str = Depends(verify_dashboard_token)
):
    """
    Manually sync order status with vendor.
    """
    # SECURITY: Validate UUID to prevent injection
    try:
        validate_uuid_format(order_id, "Order ID")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    order_service = OrderService()
    try:
        updated_order = await order_service.sync_order_status(order_id)
        return {"status": "success", "order": updated_order}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error syncing order {order_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync order: {str(e)}")


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    _: str = Depends(verify_dashboard_token)
):
    """
    Delete a user and all associated data.
    
    WARNING: This is a destructive operation. Depending on DB cascade rules,
    this may also delete related records (wallet, orders, transactions).
    """
    # SECURITY: Validate user_id format
    try:
        validate_uuid_format(user_id, "User ID")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    user_repo = BaseUserRepository()
    
    # Check if user exists
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        
        telegram_repo = TelegramUserRepository()
        whatsapp_repo = WhatsAppUserRepository()
        
        # Get platform users (for logging)
        telegram_user = await telegram_repo.get_by_user_id(user_id)
        whatsapp_user = await whatsapp_repo.get_by_user_id(user_id)
        
        # Delete platform records
        if telegram_user:
            await telegram_repo.delete(telegram_user["id"])
        if whatsapp_user:
            await whatsapp_repo.delete(whatsapp_user["id"])
        
        # Delete wallet
        wallet_repo = WalletRepository()
        wallet = await wallet_repo.get_by_user_id(user_id)
        if wallet:
            await wallet_repo.delete(wallet["id"])
        
        # Delete base user
        await user_repo.delete(user_id)
        
        logger.info(f"Deleted user {user_id}")
        return {"status": "success", "message": "User deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")


@router.post("/users/{user_id}/balance")
async def adjust_user_balance(
    user_id: str,
    amount: float = Query(..., gt=0, description="Amount to credit or debit (must be positive)"),
    type: str = Query(..., pattern="^(credit|debit)$", description="Operation type: credit or debit"),
    reason: str = Query(..., min_length=5, description="Reason for the adjustment"),
    _: str = Depends(verify_dashboard_token)
):
    """
    Adjust user balance by crediting or debiting their wallet.
    
    - **credit**: Add to balance
    - **debit**: Subtract from balance (fails if insufficient funds)
    """
    # SECURITY: Validate user_id format
    try:
        validate_uuid_format(user_id, "User ID")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Validate amount limits
    max_amount = getattr(settings, 'MAX_MANUAL_CREDIT_AMOUNT', 10000.0)
    if amount > max_amount:
        raise HTTPException(
            status_code=400, 
            detail=f"Amount exceeds maximum allowed adjustment of GHS {max_amount}"
        )
    
    # Verify user exists
    user_repo = BaseUserRepository()
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        wallet_repo = WalletRepository()
        transaction_repo = TransactionRepository()
        import uuid
        
        # Get or create wallet
        wallet = await wallet_repo.get_or_create_wallet(user_id)
        wallet_id = wallet["id"]
        
        reference = f"ADJ-{uuid.uuid4().hex[:8].upper()}"
        
        if type == "credit":
            # Credit the wallet
            new_wallet = await wallet_repo.credit_balance(wallet_id, Decimal(str(amount)))
            tx_type = "deposit"
        else:
            # Debit the wallet
            new_wallet = await wallet_repo.debit_balance(wallet_id, Decimal(str(amount)))
            tx_type = "withdrawal"
        
        # Create transaction record
        await transaction_repo.create_transaction(
            user_id=user_id,
            transaction_type=tx_type,
            amount=Decimal(str(amount)),
            currency="GHS",
            reference=reference,
            status="completed",
            provider="admin_manual",
            raw_payload={
                "reason": reason.strip(),
                "type": f"manual_{type}",
                "adjusted_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Manual {type}: user={user_id}, amount={amount}, reason={reason[:50]}")
        
        return {
            "status": "success",
            "message": f"Successfully {'credited' if type == 'credit' else 'debited'} GHS {amount}",
            "wallet": new_wallet
        }
    except ValueError as e:
        error_msg = str(e)
        if "insufficient" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Insufficient balance for debit")
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(f"Error adjusting balance for user {user_id}: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=safe_error_response(e, "adjusting balance"))


@router.post("/broadcast")
async def broadcast_message(
    platform: str = Query(..., pattern="^(telegram|whatsapp|both)$", description="Target platform"),
    message: str = Query(..., min_length=1, max_length=4096, description="Message to broadcast"),
    user_ids: Optional[str] = Query(None, description="Comma-separated user IDs (telegram_ids or phone numbers). Leave empty for all users."),
    batch_size: int = Query(20, ge=1, le=100, description="Number of messages per batch"),
    interval_seconds: int = Query(300, ge=10, le=3600, description="Seconds between batches"),
    _: str = Depends(verify_dashboard_token)
):
    """
    Send broadcast message to users on specified platform(s).
    
    The broadcast runs as a background Celery task. Returns task IDs for tracking.
    
    - **platform**: "telegram", "whatsapp", or "both"
    - **message**: Message text to send
    - **user_ids**: Optional comma-separated list. If omitted, sends to ALL users.
    - **batch_size**: How many users to message per batch (default: 20)
    - **interval_seconds**: Wait time between batches (default: 300 = 5 min)
    """
    
    # Parse user_ids if provided
    parsed_user_ids = None
    if user_ids:
        parsed_user_ids = [uid.strip() for uid in user_ids.split(",") if uid.strip()]
        if not parsed_user_ids:
            parsed_user_ids = None
    
    task_ids = {}
    
    try:
        if platform in ("telegram", "both"):
            task = broadcast_telegram.delay(
                message=message,
                user_ids=parsed_user_ids,
                batch_size=batch_size,
                interval_seconds=interval_seconds
            )
            task_ids["telegram"] = task.id
            logger.info(f"Started Telegram broadcast task: {task.id}")
        
        if platform in ("whatsapp", "both"):
            task = broadcast_whatsapp.delay(
                message=message,
                user_ids=parsed_user_ids,
                batch_size=batch_size,
                interval_seconds=interval_seconds
            )
            task_ids["whatsapp"] = task.id
            logger.info(f"Started WhatsApp broadcast task: {task.id}")
        
        return {
            "status": "queued",
            "message": f"Broadcast queued for {platform}",
            "task_ids": task_ids,
            "settings": {
                "batch_size": batch_size,
                "interval_seconds": interval_seconds,
                "target_users": "all" if not parsed_user_ids else len(parsed_user_ids)
            }
        }
    except Exception as e:
        logger.error(f"Error starting broadcast: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start broadcast: {str(e)}")
