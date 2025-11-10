from typing import List
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Get main reply keyboard."""
    keyboard = [
        ["💼 Balance", "➕ Deposit"],
        ["🌐 Bundles", "📜 History"],
        ["🎯 Referral", "❓ Help"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


def get_network_keyboard() -> InlineKeyboardMarkup:
    """Get network selection inline keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("MTN", callback_data="network:MTN"),
            InlineKeyboardButton("TELECEL", callback_data="network:VODAFONE")
        ],
        [
            InlineKeyboardButton("AIRTELTIGO", callback_data="network:AIRTELTIGO")
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data="cancel:bundles")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_bundles_keyboard(bundles: List[dict]) -> InlineKeyboardMarkup:
    """
    Get bundles inline keyboard.
    
    Args:
        bundles: List of bundle dicts with 'id', 'capacity', 'price', 'network'
    """
    buttons = []
    for bundle in bundles:
        label = f"{bundle['capacity']}GB - GHS {bundle['price']}"
        callback_data = f"bundle:{bundle['id']}"
        buttons.append([InlineKeyboardButton(label, callback_data=callback_data)])
    
    # Add back and cancel buttons
    buttons.append([
        InlineKeyboardButton("⬅️ Back to Networks", callback_data="back:networks"),
        InlineKeyboardButton("❌ Cancel", callback_data="cancel:bundles")
    ])
    
    return InlineKeyboardMarkup(buttons)


def get_phone_input_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for phone input step with cancel button."""
    keyboard = [
        [
            InlineKeyboardButton("⬅️ Back to Bundles", callback_data="back:bundles"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel:bundles")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_provider_keyboard() -> InlineKeyboardMarkup:
    """Get provider selection inline keyboard for deposits."""
    keyboard = [
        [
            InlineKeyboardButton("MTN", callback_data="provider:MTN"),
            InlineKeyboardButton("TELECEL", callback_data="provider:VODAFONE")
        ],
        [
            InlineKeyboardButton("AIRTELTIGO", callback_data="provider:AIRTELTIGO")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

