#!/bin/bash
set -e

echo "Starting entrypoint script..."

# Test Supabase connection
echo "Testing Supabase connection..."
python << EOF
from app.db.supabase_client import supabase

try:
    # Test connection by fetching user count
    response = supabase.table('users').select("count").execute()
    print("✅ Supabase connection successful!")
except Exception as e:
    print(f"❌ Supabase connection failed: {e}")
    exit(1)
EOF

# Start the application
echo "Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
