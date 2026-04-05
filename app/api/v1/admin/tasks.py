from app.core.auth import verify_admin_access
from app.services.bundle_sync import BundleSyncService
from fastapi import APIRouter, BackgroundTasks, Depends
from app.services.paystack_service import PaystackService
from app.services.blessdatahub_client import BlessdatahubClient

router = APIRouter()


@router.post("/sync-bundles")
async def sync_bundles(
    background_tasks: BackgroundTasks,
    networks: list[str] = None,
    _: str = Depends(verify_admin_access)
):
    """
    Trigger bundle synchronization.
    
    NOTE: This endpoint is DEPRECATED for Blessdatahub.
    Blessdatahub uses static pricing - use seed_bundles.sql to populate bundles.
    """
    sync_service = BundleSyncService()
    
    # Run sync in background (will log deprecation warning)
    background_tasks.add_task(
        sync_service.sync_bundles_to_db,
        networks
    )
    
    return {
        "status": "warning",
        "message": "Bundle sync is deprecated for Blessdatahub. Use seed_bundles.sql instead."
    }


@router.get("/health/blessdatahub")
async def check_blessdatahub_health():
    """Check Blessdatahub API configuration."""
    try:
        client = BlessdatahubClient()
        return {
            "status": "configured",
            "message": "Blessdatahub client is properly configured",
            "api_url": client.base_url,
            "note": "Blessdatahub does not have a dedicated health endpoint"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Blessdatahub configuration error: {str(e)}"
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
