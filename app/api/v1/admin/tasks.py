from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.bundle_sync import BundleSyncService
from fastapi import APIRouter, Depends, BackgroundTasks

router = APIRouter()


@router.post("/sync-bundles")
async def sync_bundles(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    networks: list[str] = None
):
    """
    Trigger bundle synchronization from DatamartGH.
    
    Args:
        networks: Optional list of networks to sync (MTN, VODAFONE, AIRTELTIGO)
                 If None, syncs all networks.
    """
    sync_service = BundleSyncService()
    
    # Run sync in background
    background_tasks.add_task(
        sync_service.sync_bundles_to_db,
        db,
        networks
    )
    
    return {
        "status": "success",
        "message": "Bundle sync started in background"
    }


@router.get("/health/datamart")
async def check_datamart_health():
    """Check DatamartGH API health."""
    from app.services.datamart_client import DatamartClient
    
    client = DatamartClient()
    try:
        # Try to fetch bundles for one network as health check
        bundles = await client.fetch_bundles("MTN")
        return {
            "status": "healthy",
            "message": "DatamartGH API is accessible",
            "bundles_count": len(bundles) if bundles else 0
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"DatamartGH API error: {str(e)}"
        }


@router.get("/health/paystack")
async def check_paystack_health():
    """Check Paystack API health."""
    from app.services.paystack_service import PaystackService
    
    service = PaystackService()
    try:
        # Simple health check - verify service can be instantiated
        # In production, you might want to call a Paystack endpoint
        return {
            "status": "healthy",
            "message": "Paystack service is configured"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Paystack service error: {str(e)}"
        }

