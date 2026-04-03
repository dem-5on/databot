from slowapi import Limiter
from slowapi.util import get_remote_address

# Create limiter instance
# Default limit: 60 requests per minute per IP (stricter than 100)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"]
)

# Rate limit categories for different endpoint types
# These can be used with @limiter.limit() decorator
RATE_LIMITS = {
    "strict": "5/minute",      # Financial operations (deposit, withdraw)
    "normal": "30/minute",     # Standard API calls (balance, history)
    "relaxed": "100/minute",   # High-traffic endpoints (bundle listing)
    "webhook": "50/minute",    # Webhook endpoints
    "admin": "20/minute",      # Admin operations
    "debug": "5/hour",         # Debug endpoints
}
