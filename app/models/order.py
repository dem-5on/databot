import uuid
import enum
from app.db.base import Base
from sqlalchemy import DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Column, String, Numeric, ForeignKey, Enum as SQLEnum


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("base_users.id"), nullable=False, index=True)
    bundle_id = Column(UUID(as_uuid=True), ForeignKey("bundles.id"), nullable=False, index=True)
    phone = Column(String, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    vendor_reference = Column(String, nullable=True, index=True)
    vendor_response = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # relationship  pointing to BaseUser
    user = relationship("BaseUser", back_populates="orders")
    bundle = relationship("Bundle")

