import logging
from postgrest.exceptions import APIError
from app.db.supabase_client import supabase
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository class for Supabase operations with consistent error handling."""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.client = supabase
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new record.
        
        Args:
            data: Dictionary containing the record data
            
        Returns:
            The created record
            
        Raises:
            ValueError: If creation fails
        """
        try:
            response = await self.client.table(self.table_name).insert(data).execute()
            if not response.data:
                raise ValueError(f"Failed to create record in {self.table_name}")
            logger.info(f"Created record in {self.table_name}: {data.get('id', 'N/A')}")
            return response.data[0]
        except APIError as e:
            logger.error(f"API error creating record in {self.table_name}: {str(e)}")
            raise ValueError(f"Failed to create record in {self.table_name}: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating record in {self.table_name}: {str(e)}")
            raise ValueError(f"Error creating record in {self.table_name}: {str(e)}")
    
    async def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a record by ID.
        
        Args:
            record_id: The ID of the record
            
        Returns:
            The record if found, None otherwise
        """
        try:
            response = await self.client.table(self.table_name).select("*").eq("id", record_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching record {record_id} from {self.table_name}: {str(e)}")
            return None

    async def get_by_field(self, field: str, value: Any) -> Optional[Dict[str, Any]]:
        """
        Get a single record by a specific field.
        
        Args:
            field: The field name to search by
            value: The value to search for
            
        Returns:
            The first matching record if found, None otherwise
        """
        try:
            response = await self.client.table(self.table_name).select("*").eq(field, value).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching record by {field}={value} from {self.table_name}: {str(e)}")
            return None
    
    async def get_all_by_field(
        self, 
        field: str, 
        value: Any, 
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all records matching a field value.
        
        Args:
            field: The field name to search by
            value: The value to search for
            limit: Optional limit on number of records to return
            
        Returns:
            List of matching records
        """
        try:
            query = await self.client.table(self.table_name).select("*").eq(field, value)
            if limit:
                query = query.limit(limit)
            response = await query.execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching records by {field}={value} from {self.table_name}: {str(e)}")
            return []
    
    async def update(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a record by ID.
        
        Args:
            record_id: The ID of the record to update
            data: Dictionary containing the fields to update
            
        Returns:
            The updated record
            
        Raises:
            ValueError: If update fails or record not found
        """
        try:
            response = await self.client.table(self.table_name).update(data).eq("id", record_id).execute()
            
            if not response.data:
                raise ValueError(f"No record found with id {record_id} in {self.table_name}")
                
            logger.info(f"Updated record {record_id} in {self.table_name}")
            return response.data[0]
            
        except APIError as e:
            logger.error(f"API error updating record {record_id} in {self.table_name}: {str(e)}")
            raise ValueError(f"Failed to update record in {self.table_name}: {str(e)}")
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating record {record_id} in {self.table_name}: {str(e)}")
            raise ValueError(f"Error updating record in {self.table_name}: {str(e)}")
    
    async def delete(self, record_id: str) -> bool:
        """
        Delete a record by ID.
        
        Args:
            record_id: The ID of the record to delete
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If deletion fails
        """
        try:
            response = await self.client.table(self.table_name).delete().eq("id", record_id).execute()
            logger.info(f"Deleted record {record_id} from {self.table_name}")
            return True
        except APIError as e:
            logger.error(f"API error deleting record {record_id} from {self.table_name}: {str(e)}")
            raise ValueError(f"Failed to delete record from {self.table_name}: {str(e)}")
        except Exception as e:
            logger.error(f"Error deleting record {record_id} from {self.table_name}: {str(e)}")
            raise ValueError(f"Error deleting record from {self.table_name}: {str(e)}")
    
    async def get_all(
        self, 
        limit: Optional[int] = None, 
        order_by: Optional[str] = None, 
        ascending: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all records from the table.
        
        Args:
            limit: Optional limit on number of records
            order_by: Optional field name to order by
            ascending: Sort order (True for ascending, False for descending)
            
        Returns:
            List of records
        """
        try:
            query = await self.client.table(self.table_name).select("*")
            if order_by:
                query = query.order(order_by, desc=not ascending)
            if limit:
                query = query.limit(limit)
            response = await query.execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching all records from {self.table_name}: {str(e)}")
            return []
    
    async def upsert(
        self, 
        data: Dict[str, Any], 
        on_conflict: str = "id"
    ) -> Dict[str, Any]:
        """
        Upsert a record (insert or update on conflict).
        
        Args:
            data: Dictionary containing the record data
            on_conflict: The column(s) to check for conflicts (comma-separated for multiple)
            
        Returns:
            The upserted record
            
        Raises:
            ValueError: If upsert fails
        """
        try:
            response = await self.client.table(self.table_name).upsert(
                data, 
                on_conflict=on_conflict
            ).execute()
            
            if not response.data:
                raise ValueError(f"Failed to upsert record in {self.table_name}")
                
            logger.info(f"Upserted record in {self.table_name}: {data.get('id', 'N/A')}")
            return response.data[0]
            
        except APIError as e:
            logger.error(f"API error upserting record in {self.table_name}: {str(e)}")
            raise ValueError(f"Failed to upsert record in {self.table_name}: {str(e)}")
        except Exception as e:
            logger.error(f"Error upserting record in {self.table_name}: {str(e)}")
            raise ValueError(f"Error upserting record in {self.table_name}: {str(e)}")
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records in the table.
        
        Args:
            filters: Optional dictionary of field-value pairs to filter by
            
        Returns:
            Number of records matching the filters
        """
        try:
            query = await self.client.table(self.table_name).select("*", count="exact")
            
            if filters:
                for field, value in filters.items():
                    query = query.eq(field, value)
            
            response = query.execute()
            return response.count if hasattr(response, 'count') else 0
        except Exception as e:
            logger.error(f"Error counting records in {self.table_name}: {str(e)}")
            return 0
    
    async def exists(self, record_id: str) -> bool:
        """
        Check if a record exists by ID.
        
        Args:
            record_id: The ID to check
            
        Returns:
            True if record exists, False otherwise
        """
        return (await self.get_by_id(record_id)) is not None