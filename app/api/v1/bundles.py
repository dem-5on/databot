"""Bundle API endpoints using Supabase repositories."""
from typing import Optional
from decimal import Decimal, ROUND_UP
from fastapi import APIRouter
from app.core.config import settings
from app.repository.bundle_repo import BundleRepository

router = APIRouter()


def apply_markup(cost_price: str) -> str:
    """
    Apply markup percentage to cost price.
    
    Args:
        cost_price: Original cost price as string
        
    Returns:
        Marked-up price as string (rounded up to 2 decimal places)
    """
    price = Decimal(str(cost_price))
    markup = Decimal(str(settings.PRICE_MARKUP_PERCENTAGE)) / Decimal("100")
    marked_up_price = price * (Decimal("1") + markup)
    # Round up to nearest 0.01 (ensures we don't lose margin)
    return str(marked_up_price.quantize(Decimal("0.01"), rounding=ROUND_UP))


@router.get("")
async def get_bundles(network: Optional[str] = None):
    """
    Get available bundles, optionally filtered by network.
    Prices include markup percentage from settings.
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
                "price": apply_markup(b["price"]),  # Apply markup to display price
                "currency": b.get("currency", "GHS")
            }
            for b in bundles
        ]
    }
