

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
    
    # If starts with country code, use it as it is 
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
    
    # Check if all characters are digits
    if not phone.isdigit():
        return False, "Phone number must contain only digits."
    
    # Check based on the format the user is using
    if phone.startswith("233"):
        # User is using international format (233XXXXXXXXX)
        if len(phone) == 12:
            return True, ""
        elif len(phone) > 12:
            return False, f"Phone number is more than 12 digits ({len(phone)}). For 233 format, use exactly 12 digits (e.g., 233241234567)."
        else:
            return False, f"Phone number is less than 12 digits ({len(phone)}). For 233 format, use exactly 12 digits (e.g., 233241234567)."
    
    elif phone.startswith("0"):
        # User is using local format (0XXXXXXXXX)
        if len(phone) == 10:
            return True, ""
        elif len(phone) > 10:
            return False, f"Phone number is more than 10 digits ({len(phone)}). For local format, use exactly 10 digits (e.g., 0241234567)."
        else:
            return False, f"Phone number is less than 10 digits ({len(phone)}). For local format, use exactly 10 digits (e.g., 0241234567)."
    
    else:
        # User entered digits without prefix (assume they meant local format without leading 0)
        if len(phone) == 9:
            return True, ""
        elif len(phone) > 9:
            return False, f"Phone number is more than 9 digits ({len(phone)}). Please use format: 0XXXXXXXXX or 233XXXXXXXXX."
        else:
            return False, f"Phone number is less than 9 digits ({len(phone)}). Please use format: 0XXXXXXXXX or 233XXXXXXXXX."


def detect_network(phone: str) -> str | None:
    """
    Detect mobile network from phone number prefix (Ghana networks).
    
    Args:
        phone: Phone number in any format (0XXXXXXXXX, 233XXXXXXXXX, +233XXXXXXXXX)
        
    Returns:
        Network name (MTN, VODAFONE, AIRTELTIGO) or None if not detected
    """
    # Remove whitespace, dashes, plus signs
    phone = phone.strip().replace(" ", "").replace("-", "").replace("+", "")
    
    # Extract the network prefix digits (first 2-3 digits that identify the network)
    if phone.startswith("233") and len(phone) >= 5:
        # International format: 233XXXXXXXXX -> extract first 2 digits after country code
        # Then prepend "0" to match the 0XX format (e.g., 233241234567 -> "24" -> "024")
        prefix_digits = phone[3:5]  # First 2 digits after country code
        prefix = f"0{prefix_digits}"
    elif phone.startswith("0") and len(phone) >= 4:
        # Local format: 0XXXXXXXXX -> extract first 3 digits including the 0
        prefix = phone[:3]  # "0" + next 2 digits (e.g., "024")
    elif len(phone) >= 2:
        # No country code or leading zero: extract first 2 digits and prepend "0"
        prefix_digits = phone[:2]
        prefix = f"0{prefix_digits}"
    else:
        return None
    
    # Network prefix mapping for Ghana (format: 0XX)
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

