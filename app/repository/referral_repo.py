import logging
from typing import Optional, List, Dict, Any
from decimal import Decimal
from app.repository.base import BaseRepository

logger = logging.getLogger(__name__)


class ReferralRepository(BaseRepository):
    """Repository for managing referrals."""
    
    def __init__(self):
        super().__init__("referrals")
        
    async def create_referral(
        self, 
        referrer_id: str, 
        referred_id: str, 
        referral_code: str,
        bonus_amount: Decimal = Decimal("0.10")
    ) -> Optional[Dict[str, Any]]:
        """Create a new referral record."""
        data = {
            "referrer_id": referrer_id,
            "referred_id": referred_id,
            "referral_code": referral_code,
            "bonus_amount": str(bonus_amount),
            "bonus_paid": False
        }
        return await self.create(data)

    async def get_by_referrer_id(self, referrer_id: str) -> List[Dict[str, Any]]:
        """Get all referrals by a referrer."""
        return await self.get_all_by_field("referrer_id", referrer_id)

    async def get_by_referred_id(self, referred_id: str) -> Optional[Dict[str, Any]]:
        """Get referral record where user was referred."""
        return await self.get_by_field("referred_id", referred_id)
        
    async def get_by_code(self, referral_code: str) -> List[Dict[str, Any]]:
        """Get referrals by code."""
        return await self.get_all_by_field("referral_code", referral_code)

    async def mark_bonus_paid(self, referral_id: str) -> Optional[Dict[str, Any]]:
        """Mark referral bonus as paid."""
        from datetime import datetime
        return await self.update(
            referral_id, 
            {
                "bonus_paid": True,
                "bonus_paid_at": datetime.utcnow().isoformat()
            }
        )

    async def get_unpaid_bonuses(self, referrer_id: str) -> tuple[Decimal, List[str]]:
        """
        Get total unpaid bonus amount and list of referral IDs for a user.
        """
        referrals = await self.get_by_referrer_id(referrer_id)
        unpaid = [r for r in referrals if not r.get("bonus_paid")]
        
        total_amount = sum(Decimal(str(r.get("bonus_amount", "0"))) for r in unpaid)
        referral_ids = [r["id"] for r in unpaid]
        
        return total_amount, referral_ids

    async def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top referrers.
        """
        try:
            # Fetch reasonable amount of referrals for aggregation
            # In production, this should be replaced with a database view or RPC call
            all_referrals = await self.get_all(limit=10000)
            
            referrer_counts = {}
            for ref in all_referrals:
                referrer_id = ref["referrer_id"]
                if referrer_id not in referrer_counts:
                    referrer_counts[referrer_id] = {"count": 0, "paid_count": 0, "bonus": Decimal(0)}
                
                referrer_counts[referrer_id]["count"] += 1
                if ref.get("bonus_paid"):
                    referrer_counts[referrer_id]["paid_count"] += 1
                    referrer_counts[referrer_id]["bonus"] += Decimal(str(ref.get("bonus_amount", "0")))
            
            # Sort by count desc
            sorted_referrers = sorted(
                referrer_counts.items(), 
                key=lambda x: x[1]["count"], 
                reverse=True
            )
            
            return [
                {
                    "user_id": uid,
                    "total_referrals": data["count"],
                    "total_bonus": float(data["bonus"]),
                    "conversion_rate": round((data["paid_count"] / data["count"] * 100), 1) if data["count"] > 0 else 0
                }
                for uid, data in sorted_referrers[:limit]
            ]
        except Exception as e:
            logger.error(f"Error getting referral leaderboard: {str(e)}")
            return []

    async def get_stats(self) -> Dict[str, Any]:
        """Get global referral statistics."""
        try:
            referrals = await self.get_all(limit=10000)
            total = len(referrals)
            if total == 0:
                return {
                    "total_referrals": 0,
                    "conversion_rate": 0,
                    "total_bonuses_paid": 0,
                }
            
            paid_referrals = [r for r in referrals if r.get("bonus_paid")]
            total_bonus = sum(Decimal(str(r.get("bonus_amount", "0"))) for r in paid_referrals)
            conversion_rate = (len(paid_referrals) / total) * 100
            
            return {
                "total_referrals": total,
                "conversion_rate": round(conversion_rate, 1),
                "total_bonuses_paid": float(total_bonus),
            }
        except Exception as e:
            logger.error(f"Error getting referral stats: {e}")
            return {"total_referrals": 0, "conversion_rate": 0, "total_bonuses_paid": 0}

    async def get_recent_payouts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent bonus payouts."""
        try:
            # Query referrals where bonus_paid is true, ordered by bonus_paid_at desc
            # Since Supabase client standard query might be limited, we'll fetch general recent and filter
            # Proper way: .eq("bonus_paid", True).order("bonus_paid_at", desc=True)
            
            res = await (
                self.client.table(self.table_name)
                .select("*")
                .eq("bonus_paid", True)
                .order("bonus_paid_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data if res.data else []
        except Exception as e:
            logger.error(f"Error fetching recent payouts: {e}")
            return []