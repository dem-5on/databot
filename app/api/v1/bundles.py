"""Bundle API endpoints using Supabase repositories."""
from typing import Optional
from fastapi import APIRouter
from app.repository.bundle_repo import BundleRepository

router = APIRouter()


@router.get("")
async def get_bundles(network: Optional[str] = None):
    """
    Get available bundles, optionally filtered by network.
    """
    bundle_repo = BundleRepository()
    
    if network:
        bundles = await bundle_repo.get_by_network(network.upper(), active_only=True)
    else:
        bundles = await bundle_repo.get_active_bundles()
    
    return {
        "bundles": [
            {
                "id": b["id"],
                "network": b["network"],
                "capacity": b["capacity"],
                "mb": b["mb"],
                "price": b["price"],
                "currency": b.get("currency", "GHS")
            }
            for b in bundles
        ]
    }
