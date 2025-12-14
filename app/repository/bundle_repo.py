import logging
import time
from uuid import uuid4
from decimal import Decimal
from typing import Optional, List, Dict, Any
from app.repository.base import BaseRepository

logger = logging.getLogger(__name__)

# Simple TTL cache for bundle queries
class BundleCache:
    """Time-based cache for bundle data to reduce database queries."""
    
    def __init__(self, ttl_seconds: int = 300):  # 5 minute default TTL
        self._cache: Dict[str, tuple] = {}  # key -> (data, expiry_time)
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._cache:
            data, expiry = self._cache[key]
            if time.time() < expiry:
                logger.debug(f"Cache hit for: {key}")
                return data
            else:
                del self._cache[key]
                logger.debug(f"Cache expired for: {key}")
        return None
    
    def set(self, key: str, value: Any):
        """Store value with TTL."""
        self._cache[key] = (value, time.time() + self.ttl)
        logger.debug(f"Cached: {key}")
    
    def invalidate(self, key: str = None):
        """Invalidate specific key or entire cache."""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()
            logger.info("Bundle cache cleared")

# Module-level cache instance
_bundle_cache = BundleCache(ttl_seconds=300)  # 5 minutes


class BundleRepository(BaseRepository):
    """Repository for bundle operations."""
    
    def __init__(self):
        super().__init__("bundles")
    
    async def get_by_network(
        self, 
        network: str, 
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get bundles by network (cached for 5 minutes)."""
        cache_key = f"network:{network}:active:{active_only}"
        cached = _bundle_cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            query = self.client.table(self.table_name).select("*").eq("network", network)
            if active_only:
                query = query.eq("active", True)
            response = await query.execute()
            result = response.data if response.data else []
            _bundle_cache.set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error fetching bundles for network {network}: {str(e)}")
            return []
    
    async def get_active_bundles(
        self, 
        network: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get active bundles, optionally filtered by network (cached for 5 minutes)."""
        cache_key = f"active_bundles:network:{network or 'all'}"
        cached = _bundle_cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            query = self.client.table(self.table_name).select("*").eq("active", True)
            if network:
                query = query.eq("network", network)
            response = await query.order("price", desc=False).execute()
            result = response.data if response.data else []
            _bundle_cache.set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error fetching active bundles: {str(e)}")
            return []
    
    async def upsert_bundle(
        self,
        network: str,
        capacity: str,
        mb: str,
        price: Decimal,
        currency: str = "GHS",
        active: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Upsert a bundle (insert or update based on network + capacity).
        
        This method will:
        1. Check if a bundle exists with the same network and capacity
        2. If exists, update it
        3. If not, create a new one
        
        Args:
            network: Network name (MTN, VODAFONE, AIRTELTIGO)
            capacity: Bundle capacity (e.g., "1GB", "5GB")
            mb: Bundle size in MB
            price: Bundle price
            currency: Currency (default: GHS)
            active: Whether bundle is active
            
        Returns:
            The created or updated bundle data, or None if operation fails
        """
        try:
            # First, try to find existing bundle with same network and capacity
            existing_response = await (
                self.client.table(self.table_name)
                .select("*")
                .eq("network", network)
                .eq("capacity", capacity)
                .execute()
            )
            
            bundle_data = {
                "network": network,
                "capacity": capacity,
                "mb": mb,
                "price": str(price),
                "currency": currency,
                "active": active
            }
            
            if existing_response.data and len(existing_response.data) > 0:
                # Update existing bundle
                bundle_id = existing_response.data[0]["id"]
                logger.info(f"Updating existing bundle {bundle_id} for {network} - {capacity}")
                
                # Verify bundle still exists before updating
                verify_response = await (
                    self.client.table(self.table_name)
                    .select("id")
                    .eq("id", bundle_id)
                    .execute()
                )
                
                if not verify_response.data:
                    logger.warning(f"Bundle {bundle_id} no longer exists, creating new one")
                    # If bundle was deleted, create a new one
                    bundle_data["id"] = str(uuid4())
                    result = await self.create(bundle_data)
                    _bundle_cache.invalidate()  # Clear cache after create
                    return result
                
                result = await self.update(bundle_id, bundle_data)
                _bundle_cache.invalidate()  # Clear cache after update
                return result
            else:
                # Create new bundle
                bundle_data["id"] = str(uuid4())
                logger.info(f"Creating new bundle for {network} - {capacity}")
                result = await self.create(bundle_data)
                _bundle_cache.invalidate()  # Clear cache after create
                return result
                
        except Exception as e:
            logger.error(f"Error upserting bundle {network} - {capacity}: {str(e)}")
            return None
    
    async def get_by_id(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        """Get bundle by ID."""
        try:
            response = await (
                self.client.table(self.table_name)
                .select("*")
                .eq("id", bundle_id)
                .execute()
            )
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching bundle {bundle_id}: {str(e)}")
            return None
            
    async def update(self, bundle_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a bundle with error handling.
        
        Args:
            bundle_id: The ID of the bundle to update
            data: Dictionary containing the fields to update
            
        Returns:
            The updated bundle data, or None if update fails
        """
        try:
            response = await (
                self.client.table(self.table_name)
                .update(data)
                .eq("id", bundle_id)
                .execute()
            )
                
            if not response.data or len(response.data) == 0:
                logger.warning(f"Update returned no data for bundle {bundle_id}")
                return None
                
            logger.info(f"Successfully updated bundle {bundle_id}")
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Error updating bundle {bundle_id}: {str(e)}")
            return None
            
    async def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new bundle with error handling.
        
        Args:
            data: Dictionary containing the bundle data
            
        Returns:
            The created bundle data, or None if creation fails
        """
        try:
            response = await (
                self.client.table(self.table_name)
                .insert(data)
                .execute()
            )
            
            if not response.data or len(response.data) == 0:
                logger.error("Create returned no data")
                return None
                
            logger.info(f"Successfully created bundle {data.get('id')}")
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Error creating bundle: {str(e)}")
            return None
    
    async def deactivate_bundle(self, bundle_id: str) -> bool:
        """
        Deactivate a bundle (soft delete).
        
        Args:
            bundle_id: The ID of the bundle to deactivate
            
        Returns:
            True if successful, False otherwise
        """
        result = await self.update(bundle_id, {"active": False})
        return result is not None
    
    async def activate_bundle(self, bundle_id: str) -> bool:
        """
        Activate a bundle.
        
        Args:
            bundle_id: The ID of the bundle to activate
            
        Returns:
            True if successful, False otherwise
        """
        result = await self.update(bundle_id, {"active": True})
        return result is not None
    
    async def bulk_deactivate_by_network(self, network: str) -> int:
        """
        Deactivate all bundles for a specific network.
        Useful when syncing to mark old bundles as inactive.
        
        Args:
            network: Network name
            
        Returns:
            Number of bundles deactivated
        """
        try:
            response = await (
                self.client.table(self.table_name)
                .update({"active": False})
                .eq("network", network)
                .eq("active", True)
                .execute()
            )
            
            count = len(response.data) if response.data else 0
            logger.info(f"Deactivated {count} bundles for {network}")
            return count
            
        except Exception as e:
            logger.error(f"Error bulk deactivating bundles for {network}: {str(e)}")
            return 0
    
    async def delete_by_id(self, bundle_id: str) -> bool:
        """
        Hard delete a bundle by ID.
        
        Args:
            bundle_id: The ID of the bundle to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = await (
                self.client.table(self.table_name)
                .delete()
                .eq("id", bundle_id)
                .execute()
            )
            
            success = response.data is not None
            if success:
                logger.info(f"Successfully deleted bundle {bundle_id}")
            else:
                logger.warning(f"No bundle found to delete with id {bundle_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error deleting bundle {bundle_id}: {str(e)}")
            return False
    
    async def get_all_bundles(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get all bundles from the database.
        
        Args:
            active_only: If True, only return active bundles
            
        Returns:
            List of bundle dictionaries
        """
        try:
            query = self.client.table(self.table_name).select("*")
            if active_only:
                query = query.eq("active", True)
            response = await query.order("network").order("price").execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching all bundles: {str(e)}")
            return []