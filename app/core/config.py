from typing import List, Literal
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Environment (development or production)
    ENVIRONMENT: Literal["development", "production"] = "development"
    
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

    # Maximum deposit amount in GHS
    MAXIMUM_DEPOSIT_AMOUNT: int = 1000

    # REFERAL BONUS AMOUNT in GHS
    REFERRAL_BONUS_AMOUNT: float

    # Price markup percentage
    PRICE_MARKUP_PERCENTAGE: int

    # Authentication & Security
    BOT_BACKEND_SECRET: str = ""  # Shared secret for HMAC signature verification
    ADMIN_API_KEYS: str = ""  # Comma-separated list of admin API keys
    DASHBOARD_TOKEN: str = ""  # 64-character token for monitoring dashboard access

    # Business Logic Limits
    MAX_MANUAL_CREDIT_AMOUNT: float = 100.0  # Maximum amount that can be manually credited at once

    # HTTP Connection Pool Settings
    MAX_KEEPALIVE_CONNECTIONS: int = 20
    MAX_CONNECTIONS: int = 100

    ALLOWED_ORIGINS: List[str] = [""]
    UVICORN_WORKERS: int

    # Celery Configuration
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )

    @field_validator('ENVIRONMENT')
    @classmethod
    def validate_environment(cls, v):
        """Validate environment is a known value."""
        if v.lower() not in ('development', 'production'):
            raise ValueError("ENVIRONMENT must be 'development' or 'production'")
        return v.lower()

    def validate_production_settings(self) -> List[str]:
        """
        Validate that required security settings are configured for production.
        
        Returns:
            List of missing/invalid settings (empty if all valid)
        """
        errors = []
        
        if self.ENVIRONMENT == "production":
            if not self.BOT_BACKEND_SECRET:
                errors.append("BOT_BACKEND_SECRET is required in production")
            elif len(self.BOT_BACKEND_SECRET) < 32:
                errors.append("BOT_BACKEND_SECRET should be at least 32 characters")
            
            if not self.ADMIN_API_KEYS:
                errors.append("ADMIN_API_KEYS is required in production")
            
            if not self.DASHBOARD_TOKEN:
                errors.append("DASHBOARD_TOKEN is required in production")
            elif len(self.DASHBOARD_TOKEN) < 32:
                errors.append("DASHBOARD_TOKEN should be at least 32 characters")
            
            if not self.TELEGRAM_WEBHOOK_URL and self.TELEGRAM_USE_WEBHOOK:
                errors.append("TELEGRAM_WEBHOOK_URL is required when TELEGRAM_USE_WEBHOOK is true in production")
            
            if "*" in self.ALLOWED_ORIGINS:
                errors.append("ALLOWED_ORIGINS should not contain '*' in production")
        
        return errors

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
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"


settings = Settings()

