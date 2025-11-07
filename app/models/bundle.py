from sqlalchemy import Column, String, Numeric, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import Base


class Bundle(Base):
    __tablename__ = "bundles"

    
    id = Column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4, index=True)
    network = Column(String, nullable=False, index=True)  # TELECEL, YELLO, AT_PREMIUM
    capacity = Column(String, nullable=False)  # e.g., "5" for 5GB
    mb = Column(String, nullable=False)  # e.g., "5000" for 5000MB
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, default="GHS", nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    # Unique constraint on network + capacity combination
    __table_args__ = (
        {"extend_existing": True},
    )

