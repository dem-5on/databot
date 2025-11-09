from supabase import create_client, Client
from app.core.config import settings

# Initialize Supabase client - Required for all database operations
try:
    supabase: Client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY
    )
except Exception as e:
    raise RuntimeError(
        f"Failed to initialize Supabase client: {e}. "
        "Please check SUPABASE_URL and SUPABASE_KEY environment variables."
    ) from e