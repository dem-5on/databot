"""Bundle sync API endpoints using Supabase repositories."""
from fastapi import APIRouter
from app.services.bundle_sync import BundleSyncService

router = APIRouter()


@router.post("/bundles")
async def sync_bundles(networks: list[str] = None):
    """
    Manually sync bundles from DatamartGH to database.
    """
    sync_service = BundleSyncService()
    
    try:
        count = await sync_service.sync_bundles_to_db(networks)
        return {
            "status": "success",
            "bundles_synced": count,
            "message": f"Successfully synced {count} bundles"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
