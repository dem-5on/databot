"""
Authentication and authorization utilities for the API.

This module provides FastAPI dependencies for:
- Verifying bot requests with HMAC signatures (with timestamp validation)
- Extracting user identity from headers
- Authorizing access to user-specific resources
- Validating admin API keys
"""

import hmac
import time
import hashlib
import logging
from typing import Optional
from fastapi import Header, HTTPException, Depends
from app.core.config import settings

logger = logging.getLogger(__name__)

# Maximum age of signature in seconds (5 minutes)
SIGNATURE_MAX_AGE = 300


class UserIdentity:
    """User identity extracted from request headers."""
    
    def __init__(self, user_id: str, platform: str):
        self.user_id = user_id
        self.platform = platform
    
    def __str__(self):
        return f"{self.platform}:[REDACTED]"


def _is_production() -> bool:
    """Check if running in production environment."""
    env = getattr(settings, 'ENVIRONMENT', 'development')
    return env.lower() == 'production'


async def verify_bot_request_signature(
    x_user_id: str,
    x_platform: str,
    x_signature: str,
    x_timestamp: Optional[str] = None
) -> bool:
    """
    Verify HMAC signature of bot request.
    
    Bot should generate signature as:
    HMAC-SHA256(user_id + ":" + platform + ":" + timestamp, BOT_BACKEND_SECRET)
    
    Args:
        x_user_id: User identifier (telegram_id or phone)
        x_platform: Platform name ("telegram" or "whatsapp")
        x_signature: HMAC signature from bot
        x_timestamp: Unix timestamp when signature was created (optional for backward compat)
        
    Returns:
        True if signature is valid, False otherwise
    """
    # Fail closed in production - require secret
    if not settings.BOT_BACKEND_SECRET:
        if _is_production():
            logger.error("SECURITY: BOT_BACKEND_SECRET not set in production - rejecting request")
            return False
        else:
            logger.warning("DEV MODE: BOT_BACKEND_SECRET not set - allowing request")
            return True
    
    try:
        # Validate timestamp if provided (replay attack protection)
        if x_timestamp:
            try:
                timestamp = int(x_timestamp)
                current_time = int(time.time())
                age = abs(current_time - timestamp)
                
                if age > SIGNATURE_MAX_AGE:
                    logger.warning(f"Signature too old: age={age}s, max={SIGNATURE_MAX_AGE}s")
                    return False
            except (ValueError, TypeError):
                logger.warning("Invalid timestamp format in signature")
                return False
            
            # Include timestamp in signature verification
            message = f"{x_user_id}:{x_platform}:{x_timestamp}"
        else:
            # Backward compatibility: signature without timestamp
            # SECURITY: In production, we MUST require a timestamp to prevent replay attacks
            if _is_production():
                logger.warning("SECURITY: Rejecting request without timestamp in production")
                return False
                
            message = f"{x_user_id}:{x_platform}"
        
        expected_signature = hmac.new(
            settings.BOT_BACKEND_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(x_signature, expected_signature)
        
        if not is_valid:
            # Log failure without exposing any signature content
            logger.warning(f"Invalid signature for {x_platform} request")
        
        return is_valid
    except Exception as e:
        logger.error(f"Error verifying signature: {type(e).__name__}")
        return False


async def get_user_identity(
    x_user_id: str = Header(..., alias="X-User-ID"),
    x_platform: str = Header(..., alias="X-Platform", pattern="^(telegram|whatsapp)$"),
    x_signature: str = Header(..., alias="X-Signature"),
    x_timestamp: Optional[str] = Header(None, alias="X-Timestamp")
) -> UserIdentity:
    """
    Extract and verify user identity from request headers.
    
    This dependency ensures:
    1. Required headers are present
    2. Platform is valid
    3. HMAC signature is correct
    4. Signature is not too old (replay protection)
    
    Args:
        x_user_id: User identifier from X-User-ID header
        x_platform: Platform from X-Platform header
        x_signature: HMAC signature from X-Signature header
        x_timestamp: Optional timestamp for replay protection
        
    Returns:
        UserIdentity object
        
    Raises:
        HTTPException: If authentication fails
    """
    # Verify signature
    if not await verify_bot_request_signature(x_user_id, x_platform, x_signature, x_timestamp):
        raise HTTPException(
            status_code=401,
            detail="Invalid request signature"
        )
    
    # Log with redacted user info
    logger.debug(f"Authenticated {x_platform} request")
    return UserIdentity(user_id=x_user_id, platform=x_platform)


async def verify_user_access(
    identifier: str,
    user: UserIdentity = Depends(get_user_identity)
) -> str:
    """
    Verify that the authenticated user can access the specified resource.
    
    Users can only access their own data - the identifier in the path
    must match their authenticated user_id.
    
    Args:
        identifier: Resource identifier from URL path
        user: Authenticated user identity
        
    Returns:
        The identifier if authorized
        
    Raises:
        HTTPException: If user is not authorized
    """
    if identifier != user.user_id:
        logger.warning(f"Authorization failed: {user.platform} user attempted cross-resource access")
        raise HTTPException(
            status_code=403,
            detail="You can only access your own data"
        )
    
    return identifier


async def verify_admin_access(
    x_api_key: str = Header(..., alias="X-API-Key")
) -> str:
    """
    Verify admin API key for administrative endpoints.
    
    Args:
        x_api_key: API key from X-API-Key header
        
    Returns:
        A masked key identifier (for audit logging only)
        
    Raises:
        HTTPException: If API key is invalid
    """
    if not settings.ADMIN_API_KEYS:
        if _is_production():
            logger.error("SECURITY: ADMIN_API_KEYS not configured in production")
            raise HTTPException(
                status_code=500,
                detail="Admin access not configured"
            )
        else:
            logger.warning("DEV MODE: ADMIN_API_KEYS not configured")
            raise HTTPException(
                status_code=500,
                detail="Admin access not configured"
            )
    
    # Parse comma-separated keys
    valid_keys = [key.strip() for key in settings.ADMIN_API_KEYS.split(",") if key.strip()]
    
    # Use constant-time comparison for each key
    key_valid = False
    for valid_key in valid_keys:
        if hmac.compare_digest(x_api_key, valid_key):
            key_valid = True
            break
    
    if not key_valid:
        # Log without exposing any part of the key
        logger.warning("Invalid admin API key attempt")
        raise HTTPException(
            status_code=403,
            detail="Invalid admin API key"
        )
    
    # Return masked identifier for audit trail (not the actual key)
    masked_id = f"admin_{hash(x_api_key) % 10000:04d}"
    logger.info(f"Admin access granted: {masked_id}")
    return masked_id


async def get_optional_user_identity(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_platform: Optional[str] = Header(None, alias="X-Platform"),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    x_timestamp: Optional[str] = Header(None, alias="X-Timestamp")
) -> Optional[UserIdentity]:
    """
    Optional authentication - returns user identity if headers present, None otherwise.
    
    Useful for endpoints that have both authenticated and public access.
    """
    if not x_user_id or not x_platform or not x_signature:
        return None
    
    try:
        if await verify_bot_request_signature(x_user_id, x_platform, x_signature, x_timestamp):
            return UserIdentity(user_id=x_user_id, platform=x_platform)
    except Exception:
        logger.debug("Optional authentication failed")
    
    return None


async def verify_dashboard_token(
    x_dashboard_token: str = Header(..., alias="X-Dashboard-Token")
) -> str:
    """
    Verify the token for monitoring dashboard access.
    
    Checks against:
    1. DASHBOARD_TOKEN environment variable (master token)
    2. admin_tokens table in database (dynamic tokens)
    """
    # Fail closed in production
    if not settings.DASHBOARD_TOKEN:
        if _is_production():
            logger.error("SECURITY: DASHBOARD_TOKEN not configured in production")
    
    # 1. Check Master Token from Env using constant-time comparison
    if settings.DASHBOARD_TOKEN:
        if hmac.compare_digest(x_dashboard_token, settings.DASHBOARD_TOKEN):
            logger.debug("Dashboard access via master token")
            return "master_token"
    
    # 2. Check Database Tokens
    try:
        # Import here to avoid circular dependencies
        from app.repository.admin_token_repo import AdminTokenRepository
        token_repo = AdminTokenRepository()
        if await token_repo.validate_token(x_dashboard_token):
            logger.debug("Dashboard access via database token")
            return "db_token"
    except ImportError:
        logger.warning("AdminTokenRepository not available")
    except Exception as e:
        logger.error(f"Error checking token against DB: {type(e).__name__}")

    # If we get here, token is invalid - don't log any part of the token
    logger.warning("Invalid dashboard token attempt")
    raise HTTPException(
        status_code=403,
        detail="Invalid dashboard token"
    )
