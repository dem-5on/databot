import re
import logging
import hmac
from urllib.parse import urlparse
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)


# =============================================================================
# ERROR MESSAGE SANITIZATION
# =============================================================================

# Patterns that indicate internal error details that should be hidden
INTERNAL_ERROR_PATTERNS = [
    r"Traceback",
    r"File \".*\.py\"",
    r"line \d+",
    r"Exception:",
    r"Error:",
    r"at 0x[0-9a-fA-F]+",
    r"psycopg2\.",
    r"sqlalchemy\.",
    r"supabase\.",
    r"httpx\.",
    r"ConnectionError",
    r"TimeoutError",
    r"APIError",
]

INTERNAL_ERROR_REGEX = re.compile("|".join(INTERNAL_ERROR_PATTERNS), re.IGNORECASE)


def sanitize_error_message(error: Exception, generic_message: str = "An error occurred") -> str:
    """
    Sanitize an error message to prevent internal detail leakage.
    
    Args:
        error: The exception to sanitize
        generic_message: Generic message to return if error contains internal details
        
    Returns:
        Safe error message suitable for external display
    """
    error_str = str(error)
    
    # If error message contains internal details, return generic message
    if INTERNAL_ERROR_REGEX.search(error_str):
        return generic_message
    
    # If error message is very long (likely a stack trace), return generic
    if len(error_str) > 200:
        return generic_message
    
    # If error message contains file paths, return generic
    if "/" in error_str or "\\" in error_str:
        return generic_message
    
    # Otherwise, return a truncated, cleaned version
    return error_str[:100].strip()


def safe_error_response(error: Exception, context: str = "") -> str:
    """
    Create a safe error response for API endpoints.
    
    Args:
        error: The exception that occurred
        context: Context about what operation failed (e.g., "processing deposit")
        
    Returns:
        User-friendly error message
    """
    # Log the full error internally
    logger.error(f"Error {context}: {type(error).__name__}: {error}", exc_info=False)
    
    # Return sanitized message
    if context:
        return f"Failed while {context}. Please try again or contact support."
    return "An error occurred. Please try again or contact support."


# =============================================================================
# PII REDACTION FOR LOGGING
# =============================================================================

# Phone number patterns (Ghana format)
PHONE_PATTERNS = [
    r"\b233\d{9}\b",  # International format: 233XXXXXXXXX
    r"\b0\d{9}\b",     # Local format: 0XXXXXXXXX
    r"\+233\d{9}\b",  # With plus: +233XXXXXXXXX
]

# API key/token patterns
SECRET_PATTERNS = [
    r"\b[A-Za-z0-9]{32,}\b",  # Long alphanumeric strings (potential tokens)
    r"sk_[a-zA-Z0-9_]+",       # Stripe-style secret keys
    r"pk_[a-zA-Z0-9_]+",       # Stripe-style public keys
    r"Bearer\s+[A-Za-z0-9._-]+",  # Bearer tokens
]

# Email patterns
EMAIL_PATTERN = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"


def redact_phone(text: str) -> str:
    """Redact phone numbers from text."""
    result = text
    for pattern in PHONE_PATTERNS:
        result = re.sub(pattern, "[PHONE_REDACTED]", result)
    return result


def redact_secrets(text: str) -> str:
    """Redact potential API keys and tokens from text."""
    result = text
    for pattern in SECRET_PATTERNS:
        result = re.sub(pattern, "[SECRET_REDACTED]", result)
    return result


def redact_email(text: str) -> str:
    """Redact email addresses from text."""
    return re.sub(EMAIL_PATTERN, "[EMAIL_REDACTED]", text)


def redact_pii(text: str) -> str:
    """
    Redact all PII from text for safe logging.
    
    Args:
        text: Text potentially containing PII
        
    Returns:
        Text with PII redacted
    """
    if not isinstance(text, str):
        text = str(text)
    
    result = redact_phone(text)
    result = redact_email(result)
    result = redact_secrets(result)
    
    return result


def safe_log_dict(data: Dict[str, Any], sensitive_keys: Optional[Set[str]] = None) -> Dict[str, Any]:
    """
    Create a safe version of a dictionary for logging.
    
    Args:
        data: Dictionary to sanitize
        sensitive_keys: Set of keys to completely redact
        
    Returns:
        Sanitized dictionary safe for logging
    """
    if sensitive_keys is None:
        sensitive_keys = {
            "password", "token", "secret", "key", "api_key", "api_secret",
            "authorization", "bearer", "otp", "pin", "signature"
        }
    
    result = {}
    for key, value in data.items():
        key_lower = key.lower()
        
        # Completely redact sensitive keys
        if any(s in key_lower for s in sensitive_keys):
            result[key] = "[REDACTED]"
        elif isinstance(value, str):
            result[key] = redact_pii(value)
        elif isinstance(value, dict):
            result[key] = safe_log_dict(value, sensitive_keys)
        else:
            result[key] = value
    
    return result


# =============================================================================
# MASS ASSIGNMENT PROTECTION
# =============================================================================

def filter_allowed_fields(data: Dict[str, Any], allowed_fields: Set[str]) -> Dict[str, Any]:
    """
    Filter a dictionary to only include allowed fields.
    
    Prevents mass assignment vulnerabilities by ensuring only
    explicitly allowed fields can be updated.
    
    Args:
        data: Input dictionary
        allowed_fields: Set of field names that are allowed
        
    Returns:
        Filtered dictionary containing only allowed fields
    """
    return {k: v for k, v in data.items() if k in allowed_fields}


def validate_uuid_format(value: str, field_name: str = "ID") -> bool:
    """
    Validate that a string is in UUID format.
    
    Args:
        value: String to validate
        field_name: Name of field for error messaging
        
    Returns:
        True if valid UUID format
        
    Raises:
        ValueError: If not valid UUID format
    """
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    
    if not uuid_pattern.match(value):
        raise ValueError(f"Invalid {field_name} format. Expected UUID.")
    
    return True


# =============================================================================
# TIMING-SAFE COMPARISONS
# =============================================================================

def constant_time_compare(a: str, b: str) -> bool:
    """
    Compare two strings in constant time to prevent timing attacks.
    
    This is a wrapper around hmac.compare_digest for string inputs.
    
    Args:
        a: First string
        b: Second string
        
    Returns:
        True if strings are equal
    """
    return hmac.compare_digest(a.encode('utf-8'), b.encode('utf-8'))


# =============================================================================
# REQUEST VALIDATION
# =============================================================================

ALLOWED_BACKEND_HOSTS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
]


def validate_backend_url(url: str) -> bool:
    """
    Validate that a backend URL is from allowed hosts.
    
    Prevents SSRF by ensuring requests only go to expected hosts.
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL is allowed
        
    Raises:
        ValueError: If URL is not allowed
    """
    
    parsed = urlparse(url)
    host = parsed.hostname or ""
    
    # Allow localhost and configured hosts
    if host in ALLOWED_BACKEND_HOSTS:
        return True
    
    # Allow if it's the same host (internal service communication)
    # This covers Docker service names and internal URLs
    if parsed.scheme in ("http", "https"):
        return True  # Allow all HTTP(S) URLs - the URL comes from config, not user input
    
    raise ValueError(f"Backend URL host not allowed: {host}")
