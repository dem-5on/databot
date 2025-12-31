import httpx
import logging
import uvicorn
from fastapi import FastAPI
from app.core.config import settings
from app.core.rate_limit import limiter
from contextlib import asynccontextmanager
from slowapi.errors import RateLimitExceeded
from bot.telegram_bot import start_webhook_mode, stop_webhook_mode
from slowapi import _rate_limit_exceeded_handler
from app.api.v1.sync import router as sync_bundles
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.users import router as users_router
from app.utils.backend_client import BackendAPIClient
from app.api.v1.wallet import router as wallet_router
from app.api.v1.orders import router as orders_router
from app.api.v1.bundles import router as bundles_router
from app.api.v1.admin.tasks import router as admin_router
from app.api.v1.referrals import router as referrals_router
from app.api.v1.webhooks.telegram_webhook import set_bot_application
from app.services.blessdatahub_client import BlessdatahubClient
from app.services.whatsapp_notifier import WhatsAppNotifierService
from app.api.v1.webhooks.paystack import router as paystack_webhook_router
from app.api.v1.webhooks.whatsapp import router as whatsapp_webhook_router
from app.api.v1.webhooks.telegram_webhook import router as telegram_webhook_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.system import router as system_router
from app.api.v1.health import router as health_router
from app.tasks.health_monitor import monitor_health_task
import asyncio

# ... imports end ...


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI application.
    Handles startup and shutdown events.
    """
    # Validate critical environment variables on startup
    
    required_settings = {
        "SUPABASE_URL": settings.SUPABASE_URL,
        "SUPABASE_KEY": settings.SUPABASE_KEY,
        "PAYSTACK_SECRET_KEY": settings.PAYSTACK_SECRET_KEY,
        "TELEGRAM_BOT_TOKEN": settings.TELEGRAM_BOT_TOKEN,
        "WHATSAPP_ACCESS_TOKEN": settings.WHATSAPP_ACCESS_TOKEN,
        "WHATSAPP_APP_SECRET": settings.WHATSAPP_APP_SECRET,
        "BLESSDATAHUB_API_KEY": settings.BLESSDATAHUB_API_KEY,
    }
    
    missing = [name for name, value in required_settings.items() if not value]
    if missing:
        error_msg = (
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Please check your .env file and ensure all required variables are set."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    # SECURITY: Validate production security settings
    security_errors = settings.validate_production_settings()
    if security_errors:
        error_msg = (
            f"SECURITY: Production security validation failed:\n"
            f"  - " + "\n  - ".join(security_errors)
        )
        logger.error(error_msg)
        if settings.is_production:
            raise RuntimeError(error_msg)
        else:
            logger.warning("Continuing in development mode despite security warnings")
    
    logger.info(f"✅ Environment validation passed (mode: {settings.ENVIRONMENT})")
    
    # Note: Bundle syncs are handled by Celery Beat (scheduled tasks)
    # To trigger a manual sync: from app.tasks import sync_bundles_task; sync_bundles_task.delay()
    
    # Initialize Telegram bot for webhook mode if enabled
    bot_application = None
    if settings.TELEGRAM_USE_WEBHOOK:
        try:          
            # Start the bot application for webhook processing
            bot_application = await start_webhook_mode()
            set_bot_application(bot_application)
            
            # Register webhook with Telegram
            webhook_url = f"{settings.TELEGRAM_WEBHOOK_URL}/api/v1/webhooks/telegram"
            params = {
                "url": webhook_url,
            }
            if settings.TELEGRAM_WEBHOOK_SECRET:
                params["secret_token"] = settings.TELEGRAM_WEBHOOK_SECRET
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook",
                    json=params
                )
                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        logger.info(f"✅ Telegram webhook set successfully: {webhook_url}")
                    else:
                        logger.error(f"Failed to set Telegram webhook: {result}")
                else:
                    logger.error(f"Failed to set Telegram webhook: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"Error setting up Telegram webhook: {e}")
    else:
        logger.info("Telegram webhook mode disabled - run bot separately with: python -m bot.telegram_bot")
    
    # Start background tasks
    health_task = asyncio.create_task(monitor_health_task())
    
    yield
    
    # Cancel background tasks
    health_task.cancel()
    try:
        await health_task
    except asyncio.CancelledError:
        pass

    # Clean up Telegram bot if webhook mode was enabled
    if settings.TELEGRAM_USE_WEBHOOK:
        try:            
            # Delete webhook from Telegram
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/deleteWebhook"
                )
            logger.info("Telegram webhook deleted")
            
            # Stop the bot application
            await stop_webhook_mode()
        except Exception as e:
            logger.error(f"Error cleaning up Telegram webhook: {e}")
    
    # Clean up shared HTTP clients
    try:
        await WhatsAppNotifierService.close_client()
        await BlessdatahubClient.close_client()
        await BackendAPIClient.close_client()
        logger.info("Closed shared HTTP clients")
    except Exception as e:
        logger.error(f"Error closing HTTP clients: {e}")


app = FastAPI(
    title="Intejers Data Hub API",
    lifespan=lifespan
)

# Configure rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
# If allowed_origins contains "*", allow_credentials MUST be False
# We'll set a explicit list for dev convenience
origins = settings.ALLOWED_ORIGINS
if "*" in origins:
    # In dev, we can allow everything if we don't need credentials
    # but since allow_credentials is True, we must be specific
    origins = [
        "http://localhost:8080",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(wallet_router, prefix="/api/v1/wallet", tags=["wallet"])
app.include_router(orders_router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
app.include_router(bundles_router, prefix="/api/v1/bundles", tags=["bundles"])
app.include_router(paystack_webhook_router, prefix="/api/v1/webhooks/paystack", tags=["webhooks"])
app.include_router(whatsapp_webhook_router, prefix="/api/v1/webhooks/whatsapp", tags=["webhooks"])
app.include_router(telegram_webhook_router, prefix="/api/v1/webhooks/telegram", tags=["webhooks"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(system_router, prefix="/api/v1/system", tags=["system"])
app.include_router(referrals_router, prefix="/api/v1/referrals", tags=["referrals"])
app.include_router(sync_bundles, prefix="/sync", tags=["sync"])
app.include_router(dashboard_router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(health_router, prefix="/api/v1/health", tags=["health"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Intejers Data Bundle Purchase System API"}


@app.post("/telegram")
async def telegram_redirect():
    """
    Redirect endpoint for old webhook URLs.
    Telegram may retry to this old path - return 200 to stop retries.
    """
    return {"status": "ok", "message": "Please use /api/v1/webhooks/telegram"}


if __name__ == "__main__":
    # Use multiple workers for production (handles 500+ users)
    # Set workers=1 for development/debugging
    workers = settings.UVICORN_WORKERS
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=8000, 
        workers=workers,
        reload=workers == 1  # Only enable reload in single-worker mode
    )
