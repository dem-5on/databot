"""Bundle sync service using Supabase repositories."""
from decimal import Decimal
from app.repository.bundle_repo import BundleRepository
from app.services.datamart_client import DatamartClient


class BundleSyncService:
    """Service for syncing bundles from DatamartGH to database using Supabase."""

    # Markup to add to all bundle prices (50 pesewas = GHS 0.50)
    PRICE_MARKUP = Decimal("0.50")

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
                    
                    # Add markup to the price (50 pesewas = GHS 0.50)
                    price = base_price + self.PRICE_MARKUP
                    
                    # Upsert bundle (insert or update)
                    self.bundle_repo.upsert_bundle(
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
                print(f"Error syncing {network}: {str(e)}")
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
        return self.bundle_repo.get_by_network(network, active_only=True)
