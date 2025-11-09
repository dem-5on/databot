from fastapi import APIRouter, BackgroundTasks
from app.services.bundle_sync import BundleSyncService
from app.services.datamart_client import DatamartClient
from app.services.paystack_service import PaystackService

router = APIRouter()


@router.post("/sync-bundles")
async def sync_bundles(
    background_tasks: BackgroundTasks,
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
        networks
    )
    
    return {
        "status": "success",
        "message": "Bundle sync started in background"
    }


@router.get("/health/datamart")
async def check_datamart_health():
    """Check DatamartGH API health."""
    
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
    
    service = PaystackService()
    try:
        # Simple health check - verify service can be instantiated
        await service.verify_connection()
        return {
            "status": "healthy",
            "message": "Paystack service is configured"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Paystack service error: {str(e)}"
        }
