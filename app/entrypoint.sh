#!/bin/bash
set -e

echo "Starting entrypoint script..."

# Test Supabase connection
echo "Testing Supabase connection..."
python << EOF
from app.db.supabase_client import supabase

try:
    # Test connection by fetching from base_users table
    response = supabase.table('base_users').select("id").limit(1).execute()
    print("✅ Supabase connection successful!")
except Exception as e:
    print(f"❌ Supabase connection failed: {e}")
    exit(1)
EOF

# Test Redis connection
echo "Testing Redis connection..."
python << EOF
import redis
from app.core.config import settings

try:
    r = redis.from_url(settings.CELERY_BROKER_URL)
    r.ping()
    print("✅ Redis connection successful!")
except Exception as e:
    print(f"❌ Redis connection failed: {e}")
    exit(1)
EOF

# Start the application with worker count
WORKERS=${UVICORN_WORKERS:-1}
echo "Starting FastAPI application with $WORKERS workers..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers $WORKERS
