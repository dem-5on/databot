import uuid
import enum
from app.db.base import Base
from sqlalchemy import DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Column, String, Numeric, ForeignKey, Enum as SQLEnum, JSON


class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    PURCHASE = "purchase"
    REFUND = "refund"
    REFERRAL_BONUS = "referral_bonus"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("base_users.id"), nullable=False, index=True)
    type = Column(SQLEnum(TransactionType), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, default="GHS", nullable=False)
    reference = Column(String, unique=True, nullable=False, index=True)
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False)
    phone = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # relationship pointing to BaseUser
    user = relationship("BaseUser", back_populates="transactions")