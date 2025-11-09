"""Referral service using Supabase repositories."""
import uuid
import string
import secrets
import logging
from decimal import Decimal
from app.services.notifier import NotifierService
from app.repository.user_repo import UserRepository
from app.repository.referral_repo import ReferralRepository
from app.repository.transaction_repo import TransactionRepository
from app.services.wallet_service import WalletService
from app.core.constants import TransactionType, TransactionStatus

logger = logging.getLogger(__name__)


class ReferralService:
    """Service for handling referral operations using Supabase."""

    REFERRAL_BONUS_AMOUNT = Decimal("1.0")
    REFERRAL_CODE_LENGTH = 8

    def __init__(self):
        self.user_repo = UserRepository()
        self.referral_repo = ReferralRepository()
        self.transaction_repo = TransactionRepository()
        self.wallet_service = WalletService()

    @staticmethod
    def generate_referral_code() -> str:
        """Generate a unique referral code."""
        characters = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(characters) for _ in range(ReferralService.REFERRAL_CODE_LENGTH))

    async def get_or_create_referral_code(self, user_id: str) -> str:
        """Get or create referral code for user."""
        user = await self.user_repo.get_by_id(user_id)
        
        if not user:
            raise ValueError("User not found")
        
        # If user already has a referral code, return it
        if user.get("referral_code"):
            return user["referral_code"]
        
        # Generate new referral code and ensure it's unique
        max_attempts = 10
        for _ in range(max_attempts):
            referral_code = ReferralService.generate_referral_code()
            
            # Check if code already exists
            existing = await self.user_repo.get_by_field("referral_code", referral_code)
            if not existing:
                await self.user_repo.update_user(user_id, referral_code=referral_code)
                return referral_code
        
        raise ValueError("Failed to generate unique referral code")

    async def register_referral(
        self,
        referred_user_id: str,
        referral_code: str
    ) -> bool:
        """
        Register a referral when a new user signs up with a referral code.
        
        Args:
            referred_user_id: ID of the user who was referred
            referral_code: Referral code that was used
            
        Returns:
            True if referral was registered, False if code invalid or user already referred
        """
        # Find referrer by code
        referrer = await self.user_repo.get_by_field("referral_code", referral_code)
        
        if not referrer:
            return False  # Invalid referral code
        
        # Don't allow self-referral
        if referrer["id"] == referred_user_id:
            return False
        
        # Check if user was already referred
        referred_user = await self.user_repo.get_by_id(referred_user_id)
        if not referred_user:
            return False
        
        if referred_user.get("referred_by"):
            return False  # User already referred
        
        # Check if this referral already exists
        existing_referral = await self.referral_repo.get_by_referred_id(referred_user_id)
        if existing_referral:
            return False  # Referral already registered
        
        # Register referral
        await self.user_repo.update_user(referred_user_id, referred_by=referrer["id"])
        
        await self.referral_repo.create_referral(
            referrer_id=referrer["id"],
            referred_id=referred_user_id,
            referral_code=referral_code,
            bonus_amount=str(self.REFERRAL_BONUS_AMOUNT)
        )
        
        return True

    async def award_referral_bonus(
        self,
        user_id: str
    ) -> bool:
        """
        Award referral bonus to referrer when referred user makes their first successful transaction.
        
        Args:
            user_id: ID of the user who made the transaction (referred user)
            
        Returns:
            True if bonus was awarded, False if no referral or bonus already paid
        """
        # Get user
        user = await self.user_repo.get_by_id(user_id)
        
        if not user or not user.get("referred_by"):
            return False  # No referrer
        
        # Find the referral record
        referral = await self.referral_repo.get_by_referred_id(user_id)
        
        if not referral or referral.get("bonus_paid"):
            return False  # Referral not found or bonus already paid
        
        # Check if this is the user's first successful transaction
        successful_transactions = await self.transaction_repo.get_by_user_id(user_id, limit=100)
        successful_transactions = [
            t for t in successful_transactions
            if t.get("status") == TransactionStatus.SUCCESS.value
            and t.get("type") in [TransactionType.DEPOSIT.value, TransactionType.PURCHASE.value]
        ]
        
        # Only award if this is the first successful transaction (count should be 1)
        if len(successful_transactions) != 1:
            return False
        
        # Award bonus to referrer
        try:
            referrer_id = referral["referrer_id"]
            bonus_reference = f"REF-{uuid.uuid4()}"
            
            # Create transaction record for referral bonus
            await self.transaction_repo.create_transaction(
                user_id=referrer_id,
                transaction_type=TransactionType.REFERRAL_BONUS.value,
                amount=self.REFERRAL_BONUS_AMOUNT,
                currency="GHS",
                reference=bonus_reference,
                status=TransactionStatus.SUCCESS.value,
                raw_payload={
                    "referred_user_id": user_id,
                    "referral_id": referral["id"]
                }
            )
            
            # Credit referrer's wallet
            await self.wallet_service.credit_wallet(
                user_id=referrer_id,
                amount=self.REFERRAL_BONUS_AMOUNT,
                reference=bonus_reference
            )
            
            # Mark referral bonus as paid
            await self.referral_repo.mark_bonus_paid(referral["id"])
            
            # Notify referrer about bonus
            try:
                referrer = await self.user_repo.get_by_id(referrer_id)
                
                if referrer:
                    await NotifierService.send_user_message(
                        telegram_id=int(referrer["telegram_id"]),
                        text=f"🎉 <b>Referral Bonus Earned!</b>\n\n"
                             f"You've earned GHS {self.REFERRAL_BONUS_AMOUNT} "
                             f"because someone you referred completed their first transaction!\n"
                             f"The bonus has been added to your wallet balance."
                    )
            except Exception as notify_error:
                # Don't fail if notification fails
                logger.error(f"Error notifying referrer: {str(notify_error)}")
            
            return True
        except Exception as e:
            # Log error but don't fail the main transaction
            logger.error(f"Error awarding referral bonus: {str(e)}", exc_info=True)
            return False

    async def get_user_referrals(self, user_id: str) -> list:
        """Get list of users referred by this user."""
        referrals = await self.referral_repo.get_by_referrer_id(user_id)
        
        return [
            {
                "referred_user_id": ref["referred_id"],
                "referral_code": ref["referral_code"],
                "bonus_paid": ref["bonus_paid"],
                "created_at": ref.get("created_at"),
                "bonus_paid_at": ref.get("bonus_paid_at")
            }
            for ref in referrals
        ]
