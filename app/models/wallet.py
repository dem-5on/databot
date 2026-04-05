import uuid
from app.db.base import Base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, Numeric, ForeignKey


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False, index=True)
    balance = Column(Numeric(10, 2), default=0.00, nullable=False)

    # Relationships
    user = relationship("User", back_populates="wallet")

