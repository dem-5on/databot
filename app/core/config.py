from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase - Required for database operations via REST API
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Paystack
    PAYSTACK_SECRET_KEY: str
    PAYSTACK_PUBLIC_KEY: str
    PAYSTACK_BASE_URL: str = "https://api.paystack.co"

    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_ADMIN_IDS: str  # Comma-separated list of admin Telegram IDs
    TELEGRAM_API_URL: str = "https://api.telegram.org/bot"

    WHATSAPP_BUSINESS_PHONE: str  # WhatsApp Business phone number in E.164 format (e.g., "233XXXXXXXXX") for referral links
    
    # WhatsApp Cloud API
    WHATSAPP_PHONE_NUMBER_ID: str
    WHATSAPP_ACCESS_TOKEN: str
    WHATSAPP_APP_ID: str
    WHATSAPP_APP_SECRET: str
    WHATSAPP_VERIFY_TOKEN: str  # Custom token for webhook verification
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v18.0"
    WHATSAPP_ADMIN_NUMBERS: str  
    
    # DatamartGH
    DATAMART_API_URL: str = "https://api.datamartgh.shop/api/developer"
    DATAMART_API_KEY: str

    # Backend API
    BACKEND_API_URL: str = "http://localhost:8000"

    # Purchase timeout in seconds
    PURCHASE_TIMEOUT: int

    # Minimum deposit amount in GHS
    MINIMUM_DEPOSIT_AMOUNT: int

    # REFERAL BONUS AMOUNT in GHS
    REFERRAL_BONUS_AMOUNT: float

    # Price markup percentage
    PRICE_MARKUP_PERCENTAGE: int

    # HTTP Connection Pool Settings
    MAX_KEEPALIVE_CONNECTIONS: int = 20
    MAX_CONNECTIONS: int = 100

    ALLOWED_ORIGINS: List[str] = ["*"]
    UVICORN_WORKERS: int

    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def admin_ids_list(self) -> List[int]:
        """Parse comma-separated admin IDs into list of integers."""
        if not self.TELEGRAM_ADMIN_IDS:
            return []
        return [int(id.strip()) for id in self.TELEGRAM_ADMIN_IDS.split(",") if id.strip()]
    
    @property
    def whatsapp_admin_numbers_list(self) -> List[str]:
        """Parse comma-separated WhatsApp admin phone numbers into list."""
        if not self.WHATSAPP_ADMIN_NUMBERS:
            return []
        return [num.strip() for num in self.WHATSAPP_ADMIN_NUMBERS.split(",") if num.strip()]


settings = Settings()


