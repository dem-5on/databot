from typing import List, Dict


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
        label = f"{bundle['capacity']} - GHS {bundle['price']}"
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
        label = f"{bundle['capacity']} - GHS {bundle['price']}"
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

