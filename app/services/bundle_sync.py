import logging
from decimal import Decimal
from app.core.config import settings
from app.repository.bundle_repo import BundleRepository

logger = logging.getLogger(__name__)


class BundleSyncService:
    """Service for bundle database operations.
    
    Note: Blessdatahub uses static pricing. Bundles are seeded via SQL script
    (seed_bundles.sql). The sync_bundles_to_db() method is deprecated.
    """

    # Markup percentage to add to all bundle prices (kept for future use)
    PRICE_MARKUP_PERCENTAGE = Decimal(str(settings.PRICE_MARKUP_PERCENTAGE))

    def __init__(self):
        self.bundle_repo = BundleRepository()

    async def sync_bundles_to_db(self, networks: list = None) -> int:
        """
        DEPRECATED: Blessdatahub uses static pricing.
        
        Bundles should be seeded via the seed_bundles.sql script in the project root.
        This method now returns 0 and logs a warning.
        
        Args:
            networks: Ignored (kept for backwards compatibility)
                      
        Returns:
            0 (no bundles synced)
        """
        logger.warning(
            "⚠️ sync_bundles_to_db() is DEPRECATED. "
            "Blessdatahub uses static pricing. Use seed_bundles.sql to populate bundles."
        )
        return 0

    async def get_bundles_by_network(self, network: str) -> list:
        """
        Get active bundles for a specific network.
        
        Args:
            network: Network name (MTN, VODAFONE, AIRTELTIGO)
            
        Returns:
            List of bundle dictionaries
        """
        return ( await self.bundle_repo.get_by_network(network, active_only=True))