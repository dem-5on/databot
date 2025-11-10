

def normalize_phone_number(phone: str, country_code: str = "233") -> str:
    """
    Normalize phone number to E.164 format (country code + number without leading zero).
    
    Args:
        phone: Phone number in various formats (0XXXXXXXXX, 233XXXXXXXXX, +233XXXXXXXXX)
        country_code: Country code to use if not present (default: 233 for Ghana)
        
    Returns:
        Normalized phone number in E.164 format (e.g., "233XXXXXXXXX")
    """
    # Remove all whitespace, dashes, and plus signs
    phone = phone.strip().replace(" ", "").replace("-", "").replace("+", "")
    
    # Remove leading zeros
    phone = phone.lstrip("0")
    
    # If starts with country code, use it as is
    if phone.startswith(country_code):
        return phone
    
    # Otherwise, prepend country code
    return f"{country_code}{phone}"


def validate_phone_number(phone: str) -> tuple[bool, str]:
    """
    Validate phone number format.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    phone = phone.strip().replace(" ", "").replace("-", "").replace("+", "")
    
    # Check if it's 10 digits starting with 0 (Ghana local format)
    if phone.startswith("0") and len(phone) == 10 and phone.isdigit():
        return True, ""
    
    # Check if it's 12 digits starting with 233 (Ghana international format)
    if phone.startswith("233") and len(phone) == 12 and phone.isdigit():
        return True, ""
    
    # Check if it's 9 digits (without leading zero or country code)
    if len(phone) == 9 and phone.isdigit():
        return True, ""
    
    return False, "Invalid format. Use 0XXXXXXXXX, 233XXXXXXXXX, or +233XXXXXXXXX"


def detect_network(phone: str) -> str | None:
    """
    Detect mobile network from phone number prefix (Ghana networks).
    
    Args:
        phone: Phone number (should be normalized first)
        
    Returns:
        Network name (MTN, VODAFONE, AIRTELTIGO) or None if not detected
    """
    # Normalize phone first
    normalized = normalize_phone_number(phone)
    
    # Remove country code for prefix detection (Ghana uses 233)
    if normalized.startswith("233"):
        prefix = normalized[3:6]  # Get first 3 digits after country code
    elif len(normalized) >= 3:
        prefix = normalized[:3]
    else:
        return None
    
    # Network prefix mapping for Ghana
    network_prefixes = {
        "MTN": ["024", "054", "055", "059", "053"],
        "VODAFONE": ["020", "050"],
        "AIRTELTIGO": ["027", "057", "026", "056"]
    }
    
    for network, prefixes in network_prefixes.items():
        if prefix in prefixes:
            return network
    
    return None


def format_phone_for_display(phone: str) -> str:
    """
    Format phone number for display (e.g., 233XXXXXXXXX -> +233 XX XXX XXXX).
    
    Args:
        phone: Phone number in E.164 format
        
    Returns:
        Formatted phone number for display
    """
    normalized = normalize_phone_number(phone)
    
    if normalized.startswith("233"):
        # Format as +233 XX XXX XXXX
        number = normalized[3:]
        if len(number) == 9:
            return f"+233 {number[:2]} {number[2:5]} {number[5:]}"
    
    return normalized

