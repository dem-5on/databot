from typing import Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime
from app.repository.base import BaseRepository


class ReferralRepository(BaseRepository):
    """Repository for referral operations."""
    
    def __init__(self):
        super().__init__("referrals")
    
    def get_by_referrer_id(self, referrer_id: str) -> List[Dict[str, Any]]:
        """Get referrals by referrer ID."""
        return self.get_all_by_field("referrer_id", referrer_id)
    
    def get_by_referred_id(self, referred_id: str) -> Optional[Dict[str, Any]]:
        """Get referral by referred user ID."""
        return self.get_by_field("referred_id", referred_id)
    
    def get_by_referral_code(self, referral_code: str) -> List[Dict[str, Any]]:
        """Get referrals by referral code."""
        return self.get_all_by_field("referral_code", referral_code)
    
    def create_referral(
        self,
        referrer_id: str,
        referred_id: str,
        referral_code: str,
        bonus_amount: str = "0.10"
    ) -> Dict[str, Any]:
        """Create a new referral record."""
        referral_data = {
            "id": str(uuid4()),
            "referrer_id": referrer_id,
            "referred_id": referred_id,
            "referral_code": referral_code,
            "bonus_paid": False,
            "bonus_amount": bonus_amount,
            "created_at": datetime.utcnow().isoformat()
        }
        return self.create(referral_data)
    
    def mark_bonus_paid(self, referral_id: str) -> Dict[str, Any]:
        """Mark referral bonus as paid."""
        return self.update(referral_id, {
            "bonus_paid": True,
            "bonus_paid_at": datetime.utcnow().isoformat()
        })
    
    def get_unpaid_referrals(self, referrer_id: str) -> List[Dict[str, Any]]:
        """Get unpaid referrals for a referrer."""
        response = (
            self.client.table(self.table_name)
            .select("*")
            .eq("referrer_id", referrer_id)
            .eq("bonus_paid", False)
            .execute()
        )
        return response.data if response.data else []

