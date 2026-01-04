from typing import List, Dict


def format_capacity(capacity: str) -> str:
    """
    Format capacity to ensure it has proper unit suffix (GB/MB).
    If no unit is present, assumes GB.
    
    Args:
        capacity: Capacity string from database (e.g., "1", "100", "1GB", "500MB")
        
    Returns:
        Formatted capacity with unit (e.g., "1GB", "100GB", "500MB")
    """
    cap = str(capacity).strip().upper()
    if "GB" in cap or "MB" in cap:
        return cap  # Already has unit
    return f"{cap}GB"  # Default to GB


def get_main_menu_buttons() -> List[Dict[str, str]]:
    """
    Get main menu buttons.
    
    Returns:
        List of button dictionaries with 'id' and 'title' keys
    """
    return [
        {"id": "menu_balance", "title": "💼 Balance"},
        {"id": "menu_deposit", "title": "➕ Deposit"},
        {"id": "menu_bundles", "title": "🌐 Bundles"}
    ]


def get_main_menu_buttons_extended() -> List[Dict[str, str]]:
    """
    Get extended main menu buttons (for second row).
    
    Returns:
        List of button dictionaries with 'id' and 'title' keys
    """
    return [
        {"id": "menu_history", "title": "📜 History"},
        {"id": "menu_referral", "title": "🎯 Referral"},
        {"id": "menu_help", "title": "❓ Help"}
    ]


def get_network_buttons() -> List[Dict[str, str]]:
    """
    Get network selection buttons.
    
    Returns:
        List of button dictionaries with 'id' and 'title' keys
    """
    return [
        {"id": "network_MTN", "title": "MTN"},
        {"id": "network_TELECEL", "title": "TELECEL"},
        {"id": "network_AIRTELTIGO", "title": "AIRTELTIGO"}
    ]


def get_back_cancel_buttons() -> List[Dict[str, str]]:
    """
    Get back and cancel buttons.
    
    Returns:
        List of button dictionaries with 'id' and 'title' keys
    """
    return [
        {"id": "back", "title": "⬅️ Back"},
        {"id": "cancel", "title": "❌ Cancel"}
    ]


def get_bundle_list_section(bundles: List[dict], network: str) -> Dict[str, any]:
    """
    Get bundle list section for list message.
    
    Args:
        bundles: List of bundle dicts with 'id', 'capacity', 'price', 'network'
        network: Network name
        
    Returns:
        Section dictionary for list message
    """
    rows = []
    for bundle in bundles[:10]:  # WhatsApp allows max 10 items per section
        capacity = format_capacity(bundle['capacity'])
        label = f"{capacity} - GHS {bundle['price']}"
        rows.append({
            "id": f"bundle_{bundle['id']}",
            "title": label
        })
    
    return {
        "title": f"{network} Bundles",
        "rows": rows
    }


def get_bundle_buttons_simple(bundles: List[dict]) -> List[Dict[str, str]]:
    """
    Get simple bundle buttons (up to 3 bundles).
    For more bundles, use list message instead.
    
    Args:
        bundles: List of bundle dicts (max 3)
        
    Returns:
        List of button dictionaries with 'id' and 'title' keys
    """
    buttons = []
    for bundle in bundles[:3]:
        capacity = format_capacity(bundle['capacity'])
        label = f"{capacity} - GHS {bundle['price']}"
        buttons.append({
            "id": f"bundle_{bundle['id']}",
            "title": label[:20]  # WhatsApp button title max 20 characters
        })
    return buttons


def get_yes_no_buttons() -> List[Dict[str, str]]:
    """
    Get yes/no confirmation buttons.
    
    Returns:
        List of button dictionaries
    """
    return [
        {"id": "confirm_yes", "title": "✅ Yes"},
        {"id": "confirm_no", "title": "❌ No"}
    ]

