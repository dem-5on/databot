from decimal import Decimal
from app.core.config import settings
from app.repository.bundle_repo import BundleRepository
from app.services.datamart_client import DatamartClient


class BundleSyncService:
    """Service for syncing bundles from DatamartGH to database using Supabase."""

    # Markup percentage to add to all bundle prices
    PRICE_MARKUP_PERCENTAGE = Decimal(str(settings.PRICE_MARKUP_PERCENTAGE))

    def __init__(self):
        self.datamart_client = DatamartClient()
        self.bundle_repo = BundleRepository()

    async def sync_bundles_to_db(self, networks: list = None) -> int:
        """
        Sync bundles from DatamartGH to database.
        
        Args:
            networks: List of networks to sync (MTN, VODAFONE, AIRTELTIGO). 
                     If None, syncs all networks.
                     
        Returns:
            Number of bundles synced
        """
        if networks is None:
            networks = ["MTN", "VODAFONE", "AIRTELTIGO"]
        
        total_synced = 0
        
        for network in networks:
            try:
                # Fetch bundles from DatamartGH
                bundles_data = await self.datamart_client.fetch_bundles(network)
                
                # Process each bundle
                for bundle_data in bundles_data:
                    # Skip if network doesn't match (when fetching all networks)
                    if bundle_data.get("network") != network:
                        continue
                    
                    capacity = bundle_data.get("capacity", "")
                    mb = bundle_data.get("mb", "")
                    price_str = bundle_data.get("price", "0")
                    
                    try:
                        # Get base price from DatamartGH
                        base_price = Decimal(str(price_str))
                    except (ValueError, TypeError):
                        base_price = Decimal("0")
                    
                    # Calculate markup amount (percentage of base price)
                    markup_amount = base_price * (self.PRICE_MARKUP_PERCENTAGE / Decimal("100"))
                    
                    # Add markup to the base price
                    price = base_price + markup_amount
                    
                    # Round to 2 decimal places for currency
                    price = price.quantize(Decimal("0.01"))
                    
                    # Upsert bundle (insert or update)
                    await self.bundle_repo.upsert_bundle(
                        network=network,
                        capacity=capacity,
                        mb=mb,
                        price=price,
                        currency="GHS",
                        active=True
                    )
                    
                    total_synced += 1
                
            except Exception as e:
                # Log error but continue with other networks
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error syncing {network}: {str(e)}")
                continue
        
        return total_synced

    async def get_bundles_by_network(self, network: str) -> list:
        """
        Get active bundles for a specific network.
        
        Args:
            network: Network name (MTN, VODAFONE, AIRTELTIGO)
            
        Returns:
            List of bundle dictionaries
        """
        return ( await self.bundle_repo.get_by_network(network, active_only=True))