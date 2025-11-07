import uuid
import string
import secrets
import logging
from decimal import Decimal
from sqlalchemy import select
from app.models.user import User
from app.models.referral import Referral
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import UUID
from app.services.wallet_service import WalletService

logger = logging.getLogger(__name__)


class ReferralService:
    """Service for handling referral operations."""

    REFERRAL_BONUS_AMOUNT = Decimal("0.10")  # GHS 0.1 = 10 pesewas
    REFERRAL_CODE_LENGTH = 8

    @staticmethod
    def generate_referral_code() -> str:
        """Generate a unique referral code."""
        characters = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(characters) for _ in range(ReferralService.REFERRAL_CODE_LENGTH))

    @staticmethod
    async def get_or_create_referral_code(db: AsyncSession, user_id: UUID) -> str:
        """Get or create referral code for user."""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("User not found")
        
        # If user already has a referral code, return it
        if user.referral_code:
            return user.referral_code
        
        # Generate new referral code and ensure it's unique
        max_attempts = 10
        for _ in range(max_attempts):
            referral_code = ReferralService.generate_referral_code()
            
            # Check if code already exists
            existing = await db.execute(
                select(User).where(User.referral_code == referral_code)
            )
            if existing.scalar_one_or_none() is None:
                user.referral_code = referral_code
                await db.commit()
                await db.refresh(user)
                return referral_code
        
        raise ValueError("Failed to generate unique referral code")

    @staticmethod
    async def register_referral(
        db: AsyncSession,
        referred_user_id: UUID,
        referral_code: str
    ) -> bool:
        """
        Register a referral when a new user signs up with a referral code.
        
        Args:
            db: Database session
            referred_user_id: ID of the user who was referred
            referral_code: Referral code that was used
            
        Returns:
            True if referral was registered, False if code invalid or user already referred
        """
        # Find referrer by code
        stmt = select(User).where(User.referral_code == referral_code)
        result = await db.execute(stmt)
        referrer = result.scalar_one_or_none()
        
        if not referrer:
            return False  # Invalid referral code
        
        # Don't allow self-referral
        if referrer.id == referred_user_id:
            return False
        
        # Check if user was already referred
        referred_user_stmt = select(User).where(User.id == referred_user_id)
        referred_user_result = await db.execute(referred_user_stmt)
        referred_user = referred_user_result.scalar_one_or_none()
        
        if not referred_user:
            return False
        
        if referred_user.referred_by is not None:
            return False  # User already referred
        
        # Check if this referral already exists
        existing_referral_stmt = select(Referral).where(
            Referral.referrer_id == referrer.id,
            Referral.referred_id == referred_user_id
        )
        existing_referral_result = await db.execute(existing_referral_stmt)
        if existing_referral_result.scalar_one_or_none():
            return False  # Referral already registered
        
        # Register referral
        referred_user.referred_by = referrer.id
        
        referral = Referral(
            referrer_id=referrer.id,
            referred_id=referred_user_id,
            referral_code=referral_code,
            bonus_paid=False
        )
        db.add(referral)
        await db.commit()
        
        return True

    @staticmethod
    async def award_referral_bonus(
        db: AsyncSession,
        user_id: UUID
    ) -> bool:
        """
        Award referral bonus to referrer when referred user makes their first successful transaction.
        
        Args:
            db: Database session
            user_id: ID of the user who made the transaction (referred user)
            
        Returns:
            True if bonus was awarded, False if no referral or bonus already paid
        """
        # Get user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or not user.referred_by:
            return False  # No referrer
        
        # Find the referral record
        referral_stmt = select(Referral).where(
            Referral.referred_id == user_id,
            Referral.bonus_paid == False
        )
        referral_result = await db.execute(referral_stmt)
        referral = referral_result.scalar_one_or_none()
        
        if not referral:
            return False  # Referral not found or bonus already paid
        
        # Check if this is the user's first successful transaction
        from app.models.transaction import Transaction, TransactionStatus, TransactionType
        successful_transactions_stmt = select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.status == TransactionStatus.SUCCESS,
            Transaction.type.in_([TransactionType.DEPOSIT, TransactionType.PURCHASE])
        )
        successful_transactions_result = await db.execute(successful_transactions_stmt)
        successful_transactions = successful_transactions_result.scalars().all()
        
        # Only award if this is the first successful transaction (count should be 1)
        if len(successful_transactions) != 1:
            return False
        
        # Award bonus to referrer
        try:
            # We'll create the transaction manually here for better control
            bonus_reference = f"REF-{uuid.uuid4()}"
            
            # Create transaction record for referral bonus first
            bonus_transaction = Transaction(
                user_id=referral.referrer_id,
                type=TransactionType.REFERRAL_BONUS,
                amount=ReferralService.REFERRAL_BONUS_AMOUNT,
                currency="GHS",
                reference=bonus_reference,
                status=TransactionStatus.SUCCESS,
                raw_payload={
                    "referred_user_id": str(user_id),
                    "referral_id": str(referral.id)
                }
            )
            db.add(bonus_transaction)
            await db.flush()
            
            # Credit referrer's wallet
            await WalletService.credit_wallet(
                db=db,
                user_id=referral.referrer_id,
                amount=ReferralService.REFERRAL_BONUS_AMOUNT,
                reference=bonus_reference
            )
            
            # Mark referral bonus as paid
            from sqlalchemy.sql import func
            referral.bonus_paid = True
            referral.bonus_paid_at = func.now()
            await db.commit()
            await db.refresh(referral)
            
            # Notify referrer about bonus (do this after commit to avoid transaction issues)
            try:
                from app.services.notifier import NotifierService
                referrer_stmt = select(User).where(User.id == referral.referrer_id)
                referrer_result = await db.execute(referrer_stmt)
                referrer = referrer_result.scalar_one_or_none()
                
                if referrer:
                    await NotifierService.send_user_message(
                        telegram_id=int(referrer.telegram_id),
                        text=f"🎉 <b>Referral Bonus Earned!</b>\n\n"
                             f"You've earned GHS {ReferralService.REFERRAL_BONUS_AMOUNT} "
                             f"because someone you referred completed their first transaction!\n"
                             f"The bonus has been added to your wallet balance."
                    )
            except Exception as notify_error:
                # Don't fail if notification fails
                logger.error(f"Error notifying referrer: {str(notify_error)}")
            
            return True
        except Exception as e:
            await db.rollback()
            # Log error but don't fail the main transaction
            logger.error(f"Error awarding referral bonus: {str(e)}", exc_info=True)
            return False

    @staticmethod
    async def get_user_referrals(db: AsyncSession, user_id: UUID) -> list:
        """Get list of users referred by this user."""
        stmt = select(Referral).where(Referral.referrer_id == user_id)
        result = await db.execute(stmt)
        referrals = result.scalars().all()
        
        return [
            {
                "referred_user_id": str(ref.referred_id),
                "referral_code": ref.referral_code,
                "bonus_paid": ref.bonus_paid,
                "created_at": ref.created_at.isoformat() if ref.created_at else None,
                "bonus_paid_at": ref.bonus_paid_at.isoformat() if ref.bonus_paid_at else None
            }
            for ref in referrals
        ]

