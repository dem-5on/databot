import logging
from typing import Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime
from decimal import Decimal
from app.repository.base import BaseRepository

logger = logging.getLogger(__name__)


class ReferralRepository(BaseRepository):
    """Repository for referral operations."""
    
    def __init__(self):
        super().__init__("referrals")
    
    async def get_by_referrer_id(self, referrer_id: str) -> List[Dict[str, Any]]:
        """
        Get all referrals made by a specific referrer.
        
        Args:
            referrer_id: The referrer's user ID
            
        Returns:
            List of referral records
        """
        return await self.get_all_by_field("referrer_id", referrer_id)
    
    async def get_by_referred_id(self, referred_id: str) -> Optional[Dict[str, Any]]:
        """
        Get referral record for a referred user.
        
        Args:
            referred_id: The referred user's ID
            
        Returns:
            Referral record if found, None otherwise
        """
        return await self.get_by_field("referred_id", referred_id)
    
    async def get_by_referral_code(self, referral_code: str) -> List[Dict[str, Any]]:
        """
        Get all referrals that used a specific referral code.
        
        Args:
            referral_code: The referral code
            
        Returns:
            List of referral records
        """
        return await self.get_all_by_field("referral_code", referral_code)
    
    async def create_referral(
        self,
        referrer_id: str,
        referred_id: str,
        referral_code: str,
        bonus_amount: str = "0.10"
    ) -> Dict[str, Any]:
        """
        Create a new referral record.
        
        Args:
            referrer_id: The user ID of the referrer
            referred_id: The user ID of the referred user
            referral_code: The referral code used
            bonus_amount: The bonus amount to be paid (default: "0.10")
            
        Returns:
            The created referral record
            
        Raises:
            ValueError: If referral creation fails
        """
        # Check if referred user already has a referral record
        existing = await self.get_by_referred_id(referred_id)
        if existing:
            logger.warning(f"User {referred_id} already has a referral record")
            raise ValueError(f"User {referred_id} has already been referred")
        
        # Check if user is trying to refer themselves
        if referrer_id == referred_id:
            logger.warning(f"User {referrer_id} attempted to refer themselves")
            raise ValueError("Cannot refer yourself")
        
        referral_data = {
            "id": str(uuid4()),
            "referrer_id": referrer_id,
            "referred_id": referred_id,
            "referral_code": referral_code,
            "bonus_paid": False,
            "bonus_amount": bonus_amount,
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            referral = await self.create(referral_data)
            logger.info(f"Created referral: {referrer_id} -> {referred_id} with code {referral_code}")
            return referral
        except Exception as e:
            logger.error(f"Error creating referral: {str(e)}")
            raise
    
    async def mark_bonus_paid(self, referral_id: str) -> Dict[str, Any]:
        """
        Mark referral bonus as paid.
        
        Args:
            referral_id: The referral ID
            
        Returns:
            The updated referral record
            
        Raises:
            ValueError: If update fails
        """
        try:
            referral = await self.update(referral_id, {
                "bonus_paid": True,
                "bonus_paid_at": datetime.utcnow().isoformat()
            })
            logger.info(f"Marked referral bonus as paid for referral {referral_id}")
            return referral
        except Exception as e:
            logger.error(f"Error marking bonus as paid for referral {referral_id}: {str(e)}")
            raise
    
    async def get_unpaid_referrals(self, referrer_id: str) -> List[Dict[str, Any]]:
        """
        Get unpaid referrals for a specific referrer.
        
        Args:
            referrer_id: The referrer's user ID
            
        Returns:
            List of unpaid referral records
        """
        try:
            response = await (
                self.client.table(self.table_name)
                .select("*")
                .eq("referrer_id", referrer_id)
                .eq("bonus_paid", False)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching unpaid referrals for referrer {referrer_id}: {str(e)}")
            return []
    
    async def get_paid_referrals(self, referrer_id: str) -> List[Dict[str, Any]]:
        """
        Get paid referrals for a specific referrer.
        
        Args:
            referrer_id: The referrer's user ID
            
        Returns:
            List of paid referral records
        """
        try:
            response = await (
                self.client.table(self.table_name)
                .select("*")
                .eq("referrer_id", referrer_id)
                .eq("bonus_paid", True)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching paid referrals for referrer {referrer_id}: {str(e)}")
            return []
    
    async def get_referral_count(self, referrer_id: str) -> int:
        """
        Get total number of referrals made by a referrer.
        
        Args:
            referrer_id: The referrer's user ID
            
        Returns:
            Number of referrals
        """
        referrals = await self.get_by_referrer_id(referrer_id)
        return len(referrals)
    
    async def get_unpaid_bonus_total(self, referrer_id: str) -> Decimal:
        """
        Get total unpaid bonus amount for a referrer.
        
        Args:
            referrer_id: The referrer's user ID
            
        Returns:
            Total unpaid bonus amount
        """
        unpaid = await self.get_unpaid_referrals(referrer_id)
        total = sum(Decimal(r["bonus_amount"]) for r in unpaid)
        return total
    
    async def get_paid_bonus_total(self, referrer_id: str) -> Decimal:
        """
        Get total paid bonus amount for a referrer.
        
        Args:
            referrer_id: The referrer's user ID
            
        Returns:
            Total paid bonus amount
        """
        paid = await self.get_paid_referrals(referrer_id)
        total = sum(Decimal(r["bonus_amount"]) for r in paid)
        return total
    
    async def get_referral_stats(self, referrer_id: str) -> Dict[str, Any]:
        """
        Get comprehensive referral statistics for a referrer.
        
        Args:
            referrer_id: The referrer's user ID
            
        Returns:
            Dictionary with referral statistics
        """
        try:
            all_referrals = await self.get_by_referrer_id(referrer_id)
            unpaid = [r for r in all_referrals if not r["bonus_paid"]]
            paid = [r for r in all_referrals if r["bonus_paid"]]
            
            unpaid_total = sum(Decimal(r["bonus_amount"]) for r in unpaid)
            paid_total = sum(Decimal(r["bonus_amount"]) for r in paid)
            
            return {
                "total_referrals": len(all_referrals),
                "unpaid_referrals": len(unpaid),
                "paid_referrals": len(paid),
                "unpaid_bonus_total": str(unpaid_total),
                "paid_bonus_total": str(paid_total),
                "total_bonus": str(unpaid_total + paid_total)
            }
        except Exception as e:
            logger.error(f"Error getting referral stats for referrer {referrer_id}: {str(e)}")
            return {
                "total_referrals": 0,
                "unpaid_referrals": 0,
                "paid_referrals": 0,
                "unpaid_bonus_total": "0",
                "paid_bonus_total": "0",
                "total_bonus": "0"
            }
    
    async def is_referred_user(self, user_id: str) -> bool:
        """
        Check if a user was referred by someone.
        
        Args:
            user_id: The user ID to check
            
        Returns:
            True if user was referred, False otherwise
        """
        referral = await self.get_by_referred_id(user_id)
        return referral is not None
    
    async def get_referrer_for_user(self, user_id: str) -> Optional[str]:
        """
        Get the referrer's user ID for a referred user.
        
        Args:
            user_id: The referred user's ID
            
        Returns:
            The referrer's user ID if found, None otherwise
        """
        referral = await self.get_by_referred_id(user_id)
        return referral["referrer_id"] if referral else None
    
    async def pay_all_unpaid_bonuses(self, referrer_id: str) -> List[Dict[str, Any]]:
        """
        Mark all unpaid referral bonuses as paid for a referrer.
        
        Args:
            referrer_id: The referrer's user ID
            
        Returns:
            List of updated referral records
        """
        unpaid = await self.get_unpaid_referrals(referrer_id)
        updated = []
        
        for referral in unpaid:
            try:
                updated_referral = await self.mark_bonus_paid(referral["id"])
                updated.append(updated_referral)
            except Exception as e:
                logger.error(f"Error paying bonus for referral {referral['id']}: {str(e)}")
                continue
        
        logger.info(f"Paid {len(updated)} bonuses for referrer {referrer_id}")
        return updated
    
    async def get_recent_referrals(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most recent referrals across all users.
        
        Args:
            limit: Maximum number of referrals to return
            
        Returns:
            List of recent referral records
        """
        return await self.get_all(limit=limit, order_by="created_at", ascending=False)