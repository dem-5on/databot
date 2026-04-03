import logging
from typing import Any
from app.core.config import settings
from app.repository.settings_repo import SettingsRepository

logger = logging.getLogger(__name__)

class SettingsService:
    """Service for retrieving system settings with fallback to static config."""
    
    def __init__(self):
        self.repo = SettingsRepository()
    
    async def get_setting(self, key: str, default: Any = None) -> Any:
        try:
            val = await self.repo.get_setting(key)
            if val is not None:
                return val
            return default
        except Exception as e:
            logger.error(f"Error fetching setting {key}: {e}")
            return default

    async def get_min_deposit_amount(self) -> float:
        """Get minimum deposit amount."""
        try:
            val = await self.get_setting("min_deposit", settings.MINIMUM_DEPOSIT_AMOUNT)
            return float(val)
        except (ValueError, TypeError):
            return float(settings.MINIMUM_DEPOSIT_AMOUNT)

    async def get_max_deposit_amount(self) -> float:
        """Get maximum deposit amount."""
        try:
            val = await self.get_setting("max_deposit", settings.MAXIMUM_DEPOSIT_AMOUNT)
            return float(val)
        except (ValueError, TypeError):
            return float(settings.MAXIMUM_DEPOSIT_AMOUNT)

    async def get_referral_bonus_amount(self) -> float:
        """Get referral bonus amount."""
        try:
            val = await self.get_setting("referral_bonus", settings.REFERRAL_BONUS_AMOUNT)
            return float(val)
        except (ValueError, TypeError):
            return float(settings.REFERRAL_BONUS_AMOUNT)

