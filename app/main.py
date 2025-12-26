import logging
import uvicorn
from fastapi import FastAPI
from app.core.config import settings
from app.core.rate_limit import limiter
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
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
from app.services.whatsapp_notifier import WhatsAppNotifierService
from app.services.blessdatahub_client import BlessdatahubClient
from app.api.v1.webhooks.paystack import router as paystack_webhook_router
from app.api.v1.webhooks.whatsapp import router as whatsapp_webhook_router


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
    
    logger.info("✅ Environment validation passed")
    
    # Note: Bundle syncs are handled by Celery Beat (scheduled tasks)
    # To trigger a manual sync: from app.tasks import sync_bundles_task; sync_bundles_task.delay()
    
    yield
    
    # Shutdown logic
    
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

allowed_origins = settings.ALLOWED_ORIGINS
# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
