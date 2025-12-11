import logging
import uvicorn

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from app.api.v1.sync import router as sync_bundles
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.users import router as users_router
from app.api.v1.wallet import router as wallet_router
from app.api.v1.orders import router as orders_router
from app.api.v1.bundles import router as bundles_router
from app.api.v1.admin.tasks import router as admin_router
from app.api.v1.referrals import router as referrals_router
from app.api.v1.webhooks.paystack import router as paystack_webhook_router
from app.api.v1.webhooks.whatsapp import router as whatsapp_webhook_router
from app.services.scheduler import start_scheduler, stop_scheduler, sync_bundles_job
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.rate_limit import limiter


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI application.
    Handles startup and shutdown events.
    """
    # Validate critical environment variables on startup
    from app.core.config import settings
    
    required_settings = {
        "SUPABASE_URL": settings.SUPABASE_URL,
        "SUPABASE_KEY": settings.SUPABASE_KEY,
        "PAYSTACK_SECRET_KEY": settings.PAYSTACK_SECRET_KEY,
        "TELEGRAM_BOT_TOKEN": settings.TELEGRAM_BOT_TOKEN,
        "WHATSAPP_ACCESS_TOKEN": settings.WHATSAPP_ACCESS_TOKEN,
        "WHATSAPP_APP_SECRET": settings.WHATSAPP_APP_SECRET,
        "DATAMART_API_KEY": settings.DATAMART_API_KEY,
    }
    
    missing = [name for name, value in required_settings.items() if not value]
    if missing:
        error_msg = (
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Please check your .env file and ensure all required variables are set."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    logger.info("✅ Environment validation passed")
    
    # Startup logic
    logger.info("Running initial bundle sync...")
    await sync_bundles_job()
    
    # Start scheduler for daily syncs
    start_scheduler()
    
    yield
    
    # Shutdown logic
    stop_scheduler()
    
    # Clean up shared HTTP clients
    try:
        from app.services.whatsapp_notifier import WhatsAppNotifierService
        from app.utils.backend_client import BackendAPIClient
        await WhatsAppNotifierService.close_client()
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
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
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(referrals_router, prefix="/api/v1/referrals", tags=["referrals"])
app.include_router(sync_bundles, prefix="/sync", tags=["sync"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Intejers Data Bundle Purchase System API"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
