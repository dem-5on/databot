from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Paystack
    PAYSTACK_SECRET_KEY: str
    PAYSTACK_PUBLIC_KEY: str
    PAYSTACK_BASE_URL: str = "https://api.paystack.co"

    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_ADMIN_IDS: str  # Comma-separated list of admin Telegram IDs
    TELEGRAM_API_URL: str = "https://api.telegram.org/bot"

    # DatamartGH
    DATAMART_API_URL: str = "https://api.datamartgh.shop/api/developer"
    DATAMART_API_KEY: str

    # Backend API
    BACKEND_API_URL: str = "http://localhost:8000"

    # Purchase timeout in seconds
    PURCHASE_TIMEOUT: int = 60

    # Minimum deposit amount in GHS
    MINIMUM_DEPOSIT_AMOUNT: int = 1

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def admin_ids_list(self) -> List[int]:
        """Parse comma-separated admin IDs into list of integers."""
        if not self.TELEGRAM_ADMIN_IDS:
            return []
        return [int(id.strip()) for id in self.TELEGRAM_ADMIN_IDS.split(",") if id.strip()]


settings = Settings()

