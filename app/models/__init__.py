"""
SQLAlchemy Models - DEPRECATED for database operations

These models are kept for reference only and are not used for database operations.
All database operations use Supabase REST API via repository classes.

The models are imported here for backward compatibility, but the enums (TransactionStatus,
TransactionType, OrderStatus) are now available in app.core.constants.

See app/repository/ for the new implementation.
"""

# Import models (these require SQLAlchemy Base, which is restored in app.db.base)
# Models are kept for reference only - not used for database operations
try:
    from app.models.user import User
    from app.models.wallet import Wallet
    from app.models.transaction import Transaction, TransactionStatus, TransactionType
    from app.models.bundle import Bundle
    from app.models.order import Order, OrderStatus
    from app.models.referral import Referral
    
    __all__ = ["User", "Wallet", "Transaction", "Bundle", "Order", "Referral",
               "TransactionStatus", "TransactionType", "OrderStatus"]
except ImportError:
    # If SQLAlchemy is not installed, models won't import
    # This is fine since we use Supabase REST API
    __all__ = []

