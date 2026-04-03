import uuid
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, ForeignKey, String


class User():
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    telegram_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    provider = Column(String, nullable=True)  # MTN, VODAFONE, AIRTELTIGO
    referral_code = Column(String, unique=True, nullable=True, index=True)  # User's unique referral code
    referred_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)  # User who referred them

    # Relationships
    wallet = relationship("Wallet", back_populates="user", uselist=False)
    transactions = relationship("Transaction", back_populates="user")
    orders = relationship("Order", back_populates="user")
    referrals_made = relationship("Referral", foreign_keys="Referral.referrer_id", back_populates="referrer")
    referral_received = relationship("Referral", foreign_keys="Referral.referred_id", back_populates="referred")

