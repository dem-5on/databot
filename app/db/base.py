"""
SQLAlchemy Base - DEPRECATED for database operations

This module is kept for backward compatibility so that model files can be imported.
The Base class is restored so that SQLAlchemy models can be imported without errors,
even though we're using Supabase REST API for all database operations.

All database operations now use Supabase REST API via repository classes.
See app/repository/ for the new implementation.

Note: Models are kept for reference only and are not used for database operations.
"""

# Restore Base class so models can be imported (for enum access)
# Models are not used for database operations, but enums are used by services
try:
    from sqlalchemy.orm import DeclarativeBase
    
    class Base(DeclarativeBase):
        """SQLAlchemy Base class - kept for model imports only."""
        pass
except ImportError:
    # If SQLAlchemy is not installed, create a dummy Base class
    class Base:
        """Dummy Base class when SQLAlchemy is not installed."""
        pass
