from decimal import Decimal
from sqlalchemy import select
from app.models.bundle import Bundle
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.datamart_client import DatamartClient


class BundleSyncService:
    """Service for syncing bundles from DatamartGH to database."""

    # Markup to add to all bundle prices (50 pesewas = GHS 0.50)
    PRICE_MARKUP = Decimal("0.50")

    def __init__(self):
        self.datamart_client = DatamartClient()

    async def sync_bundles_to_db(self, db: AsyncSession, networks: list = None) -> int:
        """
        Sync bundles from DatamartGH to database.
        
        Args:
            db: Database session
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
                    
                    # Check if bundle exists
                    existing = await db.execute(
                        select(Bundle).where(
                            Bundle.network == network,
                            Bundle.capacity == capacity
                        )
                    )
                    existing_bundle = existing.scalar_one_or_none()
                    
                    if existing_bundle:
                        # Update existing bundle
                        existing_bundle.mb = mb
                        existing_bundle.price = price
                        existing_bundle.active = True
                    else:
                        # Create new bundle
                        new_bundle = Bundle(
                            network=network,
                            capacity=capacity,
                            mb=mb,
                            price=price,
                            currency="GHS",
                            active=True
                        )
                        db.add(new_bundle)
                    
                    total_synced += 1
                
                await db.commit()
                
            except Exception as e:
                await db.rollback()
                # Log error but continue with other networks
                print(f"Error syncing {network}: {str(e)}")
                continue
        
        return total_synced

    async def get_bundles_by_network(
        self,
        db: AsyncSession,
        network: str
    ) -> list[Bundle]:
        """
        Get active bundles for a specific network.
        
        Args:
            db: Database session
            network: Network name (MTN, VODAFONE, AIRTELTIGO)
            
        Returns:
            List of Bundle models
        """
        stmt = select(Bundle).where(
            Bundle.network == network,
            Bundle.active == True
        ).order_by(Bundle.price)
        
        result = await db.execute(stmt)
        return list(result.scalars().all())

