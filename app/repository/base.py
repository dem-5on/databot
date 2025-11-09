from postgrest.exceptions import APIError
from app.db.supabase_client import supabase
from typing import Optional, List, Dict, Any


class BaseRepository:
    """Base repository class for Supabase operations."""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.client = supabase
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record."""
        response = self.client.table(self.table_name).insert(data).execute()
        if not response.data:
            raise ValueError(f"Failed to create record in {self.table_name}")
        return response.data[0]
    
    def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a record by ID."""
        response = self.client.table(self.table_name).select("*").eq("id", record_id).execute()
        return response.data[0] if response.data else None
    
    def get_by_field(self, field: str, value: Any) -> Optional[Dict[str, Any]]:
        """Get a record by a specific field."""
        response = self.client.table(self.table_name).select("*").eq(field, value).execute()
        return response.data[0] if response.data else None
    
    def get_all_by_field(self, field: str, value: Any, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all records matching a field."""
        query = self.client.table(self.table_name).select("*").eq(field, value)
        if limit:
            query = query.limit(limit)
        response = query.execute()
        return response.data if response.data else []
    
    def update(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a record by ID."""
        response = self.client.table(self.table_name).update(data).eq("id", record_id).execute()
        if not response.data:
            raise ValueError(f"Failed to update record {record_id} in {self.table_name}")
        return response.data[0]
    
    def delete(self, record_id: str) -> bool:
        """Delete a record by ID."""
        response = self.client.table(self.table_name).delete().eq("id", record_id).execute()
        return True
    
    def get_all(self, limit: Optional[int] = None, order_by: Optional[str] = None, ascending: bool = True) -> List[Dict[str, Any]]:
        """Get all records."""
        query = self.client.table(self.table_name).select("*")
        if order_by:
            query = query.order(order_by, desc=not ascending)
        if limit:
            query = query.limit(limit)
        response = query.execute()
        return response.data if response.data else []
    
    def upsert(self, data: Dict[str, Any], on_conflict: str = "id") -> Dict[str, Any]:
        """Upsert a record (insert or update on conflict)."""
        response = self.client.table(self.table_name).upsert(data, on_conflict=on_conflict).execute()
        if not response.data:
            raise ValueError(f"Failed to upsert record in {self.table_name}")
        return response.data[0]
    
    def update(self, record_id: str, data: Dict[str, Any]) -> dict:
        try:
            response = self.client.table(self.table_name)\
                .update(data)\
                .eq('id', record_id)\
                .execute()
            
            if not response.data:
                raise ValueError(f"No record found with id {record_id}")
                
            return response.data[0]
            
        except APIError as e:
            raise ValueError(f"Failed to update {self.table_name}: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error updating {self.table_name}: {str(e)}")

