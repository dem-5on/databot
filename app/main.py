import logging
from fastapi import FastAPI
from app.api.v1.sync import router as sync_bundles
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.users import router as users_router
from app.api.v1.wallet import router as wallet_router
from app.api.v1.orders import router as orders_router
from app.api.v1.bundles import router as bundles_router
from app.api.v1.admin.tasks import router as admin_router
from app.api.v1.referrals import router as referrals_router
from app.api.v1.webhooks.paystack import router as paystack_webhook_router
from app.services.scheduler import start_scheduler, stop_scheduler, sync_bundles_job


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="Data Bundle Purchase System(Intejers)",
    description="API for purchasing mobile data bundles via Telegram bot",
    version="1.0.0"
)

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
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(referrals_router, prefix="/api/v1/referrals", tags=["referrals"])
app.include_router(sync_bundles, prefix="/sync", tags=["sync"])


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    # Sync bundles immediately on startup
    logger.info("Running initial bundle sync...")
    await sync_bundles_job()
    
    # Start scheduler for daily syncs
    start_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    stop_scheduler()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Intejers Data Bundle Purchase System API"}

