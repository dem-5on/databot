"""Celery app configuration."""
from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "databot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"]  # Include task modules
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    
    # Beat schedule for periodic tasks
    # Note: Bundle sync is disabled - Blessdatahub uses static pricing
    # Bundles are seeded via SQL script (seed_bundles.sql)
    beat_schedule={},
)
