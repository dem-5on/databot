import uuid
from app.db.base import Base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, ForeignKey, Boolean, DateTime


class Referral(Base):
    """Model to track referrals and bonus payments."""
    __tablename__ = "referrals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    referrer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    referred_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    referral_code = Column(String, nullable=False, index=True)  # The code that was used
    bonus_paid = Column(Boolean, default=False, nullable=False)  # Whether bonus has been paid
    bonus_amount = Column(String, default="0.10", nullable=False)  # GHS 0.1 = 10 pesewas
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    bonus_paid_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    referrer = relationship("User", foreign_keys=[referrer_id], back_populates="referrals_made")
    referred = relationship("User", foreign_keys=[referred_id], back_populates="referral_received")

