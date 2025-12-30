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
    
    # Telegram Webhook Configuration (Production)
    TELEGRAM_WEBHOOK_URL: str = ""  # Required in production (e.g., https://api.yourdomain.com)
    TELEGRAM_WEBHOOK_SECRET: str = ""  # Secret token for webhook validation
    TELEGRAM_USE_WEBHOOK: bool = True  # Set to True for production webhook mode

    WHATSAPP_BUSINESS_PHONE: str  # WhatsApp Business phone number in E.164 format (e.g., "233XXXXXXXXX") for referral links
    
    # WhatsApp Cloud API
    WHATSAPP_PHONE_NUMBER_ID: str
    WHATSAPP_ACCESS_TOKEN: str
    WHATSAPP_APP_ID: str
    WHATSAPP_APP_SECRET: str
    WHATSAPP_VERIFY_TOKEN: str  # Custom token for webhook verification
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v18.0"
    WHATSAPP_ADMIN_NUMBERS: str  

    # Blessdatahub
    BLESSDATAHUB_API_URL: str = "https://www.blessdatahub.com/api"
    BLESSDATAHUB_API_KEY: str
    BLESSDATAHUB_API_SECRET: str
    BLESSDATAHUB_PURCHASE_TIMEOUT: int

    # Backend API
    BACKEND_API_URL: str = ""

    # Purchase timeout in seconds
    PURCHASE_TIMEOUT: int

    # Minimum deposit amount in GHS
    MINIMUM_DEPOSIT_AMOUNT: int

    # REFERAL BONUS AMOUNT in GHS
    REFERRAL_BONUS_AMOUNT: float

    # Price markup percentage
    PRICE_MARKUP_PERCENTAGE: int

    # Authentication & Security
    BOT_BACKEND_SECRET: str = ""  # Shared secret for HMAC signature verification
    ADMIN_API_KEYS: str = ""  # Comma-separated list of admin API keys
    DASHBOARD_TOKEN: str = ""  # 64-character token for monitoring dashboard access

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
