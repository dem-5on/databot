"""
Authentication and authorization utilities for the API.

This module provides FastAPI dependencies for:
- Verifying bot requests with HMAC signatures
- Extracting user identity from headers
- Authorizing access to user-specific resources
- Validating admin API keys
"""

import hmac
import hashlib
import logging
from typing import Tuple, Optional
from fastapi import Header, HTTPException, Depends
from app.core.config import settings

logger = logging.getLogger(__name__)


class UserIdentity:
    """User identity extracted from request headers."""
    
    def __init__(self, user_id: str, platform: str):
        self.user_id = user_id
        self.platform = platform
    
    def __str__(self):
        return f"{self.platform}:{self.user_id}"


async def verify_bot_request_signature(
    x_user_id: str,
    x_platform: str,
    x_signature: str
) -> bool:
    """
    Verify HMAC signature of bot request.
    
    Bot should generate signature as:
    HMAC-SHA256(user_id + ":" + platform, BOT_BACKEND_SECRET)
    
    Args:
        x_user_id: User identifier (telegram_id or phone)
        x_platform: Platform name ("telegram" or "whatsapp")
        x_signature: HMAC signature from bot
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not settings.BOT_BACKEND_SECRET:
        logger.warning("BOT_BACKEND_SECRET not set - signature verification disabled")
        return True  # Allow requests if secret not configured
    
    try:
        # Generate expected signature
        message = f"{x_user_id}:{x_platform}"
        expected_signature = hmac.new(
            settings.BOT_BACKEND_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(x_signature, expected_signature)
        
        if not is_valid:
            logger.warning(
                f"Invalid signature for {x_platform} user {x_user_id}. "
                f"Expected: {expected_signature[:8]}..., Got: {x_signature[:8]}..."
            )
        
        return is_valid
    except Exception as e:
        logger.error(f"Error verifying signature: {e}")
        return False


async def get_user_identity(
    x_user_id: str = Header(..., alias="X-User-ID"),
    x_platform: str = Header(..., alias="X-Platform", regex="^(telegram|whatsapp)$"),
    x_signature: str = Header(..., alias="X-Signature")
) -> UserIdentity:
    """
    Extract and verify user identity from request headers.
    
    This dependency ensures:
    1. Required headers are present
    2. Platform is valid
    3. HMAC signature is correct (if BOT_BACKEND_SECRET is set)
    
    Args:
        x_user_id: User identifier from X-User-ID header
        x_platform: Platform from X-Platform header
        x_signature: HMAC signature from X-Signature header
        
    Returns:
        UserIdentity object
        
    Raises:
        HTTPException: If authentication fails
        
    Example:
        @router.get("/balance/{identifier}")
        async def get_balance(
            identifier: str,
            user: UserIdentity = Depends(get_user_identity)
        ):
            # user.user_id and user.platform are verified
            ...
    """
    # Verify signature
    if not await verify_bot_request_signature(x_user_id, x_platform, x_signature):
        raise HTTPException(
            status_code=401,
            detail="Invalid request signature. Ensure bot is using correct BOT_BACKEND_SECRET."
        )
    
    logger.info(f"Authenticated request from {x_platform} user: {x_user_id}")
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
        
    Example:
        @router.get("/{identifier}/history")
        async def get_history(
            identifier: str = Depends(verify_user_access)
        ):
            # identifier is verified to match authenticated user
            ...
    """
    if identifier != user.user_id:
        logger.warning(
            f"Authorization failed: {user} attempted to access {identifier}"
        )
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
        The API key (for audit logging)
        
    Raises:
        HTTPException: If API key is invalid
        
    Example:
        @router.get("/admin/users")
        async def list_users(
            admin_key: str = Depends(verify_admin_access)
        ):
            # admin_key can be logged for audit trail
            ...
    """
    if not settings.ADMIN_API_KEYS:
        logger.error("ADMIN_API_KEYS not configured in environment")
        raise HTTPException(
            status_code=500,
            detail="Admin access not configured"
        )
    
    # Parse comma-separated keys
    valid_keys = [key.strip() for key in settings.ADMIN_API_KEYS.split(",") if key.strip()]
    
    if x_api_key not in valid_keys:
        logger.warning(f"Invalid admin API key attempt: {x_api_key[:8]}...")
        raise HTTPException(
            status_code=403,
            detail="Invalid admin API key"
        )
    
    # Log successful admin access (key prefix only for security)
    logger.info(f"Admin access granted with key: {x_api_key[:8]}...")
    return x_api_key


async def get_optional_user_identity(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_platform: Optional[str] = Header(None, alias="X-Platform"),
    x_signature: Optional[str] = Header(None, alias="X-Signature")
) -> Optional[UserIdentity]:
    """
    Optional authentication - returns user identity if headers present, None otherwise.
    
    Useful for endpoints that have both authenticated and public access.
    
    Args:
        x_user_id: Optional user identifier
        x_platform: Optional platform
        x_signature: Optional signature
        
    Returns:
        UserIdentity if authenticated, None otherwise
    """
    if not x_user_id or not x_platform or not x_signature:
        return None
    
    try:
        if await verify_bot_request_signature(x_user_id, x_platform, x_signature):
            return UserIdentity(user_id=x_user_id, platform=x_platform)
    except Exception as e:
        logger.warning(f"Optional authentication failed: {e}")
    
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
    # 1. Check Master Token from Env
    if settings.DASHBOARD_TOKEN and x_dashboard_token == settings.DASHBOARD_TOKEN:
        return x_dashboard_token
    
    # 2. Check Database Tokens
    try:
        # Import here to avoid circular dependencies
        from app.repository.admin_token_repo import AdminTokenRepository
        token_repo = AdminTokenRepository()
        if await token_repo.validate_token(x_dashboard_token):
            return x_dashboard_token
    except ImportError:
        logger.warning("AdminTokenRepository not available")
    except Exception as e:
        logger.error(f"Error checking token against DB: {e}")

    # If we get here, token is invalid
    logger.warning(f"Invalid dashboard token attempt: {x_dashboard_token[:8]}...")
    raise HTTPException(
        status_code=403,
        detail="Invalid dashboard token"
    )
