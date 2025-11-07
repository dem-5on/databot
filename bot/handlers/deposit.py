import httpx
from decimal import Decimal
from telegram import Update
from app.core.config import settings
from telegram.ext import ContextTypes, ConversationHandler

# Conversation states
AMOUNT, PHONE, OTP = range(3)

# Network prefix mapping
NETWORK_PREFIXES = {
    "MTN": ["024", "054", "055", "059", "053"],
    "VODAFONE": ["020", "050"],
    "AIRTELTIGO": ["027", "057", "026", "056"]
}


def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number to standard format (0XXXXXXXXX).
    
    Args:
        phone: Phone number in format 0XXXXXXXXX or 233XXXXXXXXX
        
    Returns:
        Normalized phone number starting with 0
    """
    phone = phone.strip().replace(" ", "").replace("-", "")
    
    # If starts with 233, convert to 0 format
    if phone.startswith("233") and len(phone) == 12:
        phone = "0" + phone[3:]
    
    return phone


def detect_network(phone: str) -> str | None:
    """
    Detect mobile network from phone number prefix.
    
    Args:
        phone: Phone number (should be normalized first)
        
    Returns:
        Network name (MTN, VODAFONE, AIRTELTIGO) or None if not detected
    """
    if len(phone) < 10:
        return None
    
    prefix = phone[:3]
    
    for network, prefixes in NETWORK_PREFIXES.items():
        if prefix in prefixes:
            return network
    
    return None


def validate_phone_number(phone: str) -> tuple[bool, str]:
    """
    Validate phone number format.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    phone = phone.strip().replace(" ", "").replace("-", "")
    
    # Check if it's 10 digits starting with 0
    if phone.startswith("0") and len(phone) == 10 and phone.isdigit():
        return True, ""
    
    # Check if it's 12 digits starting with 233
    if phone.startswith("233") and len(phone) == 12 and phone.isdigit():
        return True, ""
    
    return False, "Invalid format. Use 0XXXXXXXXX or 233XXXXXXXXX"


async def deposit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start deposit flow."""
    await update.message.reply_text(
        "➕ Deposit Funds\n\n"
        "Please enter the amount you want to deposit (GHS):\n"
        "Example: 50.00"
    )
    return AMOUNT


async def deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle amount input."""
    try:
        amount = Decimal(update.message.text.strip())
        if amount < settings.MINIMUM_DEPOSIT_AMOUNT:
            await update.message.reply_text(
                f"❌ Minimum deposit amount is GHS {settings.MINIMUM_DEPOSIT_AMOUNT}. Please enter a valid amount:"
            )
            return AMOUNT
        
        context.user_data['deposit_amount'] = str(amount)
        
        await update.message.reply_text(
            "📱 Please enter your phone number:\n"
            "Example: 0XXXXXXXXX or 233XXXXXXXXX"
        )
        return PHONE
    except (ValueError, TypeError, Exception):
        await update.message.reply_text(
            "❌ Invalid amount. Please enter a valid number (e.g., 50):"
        )
        return AMOUNT

async def deposit_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle phone input with auto network detection."""
    phone = update.message.text.strip()
    
    # Validate phone format
    is_valid, error_msg = validate_phone_number(phone)
    if not is_valid:
        await update.message.reply_text(
            f"❌ {error_msg}\n\n"
            "Please enter a valid phone number:\n"
            "Example: 0XXXXXXXXX or 233XXXXXXXXX"
        )
        return PHONE
    
    # Normalize phone number
    normalized_phone = normalize_phone_number(phone)
    
    # Detect network
    network = detect_network(normalized_phone)
    if not network:
        await update.message.reply_text(
            "❌ Could not detect network from phone number.\n\n"
            "Supported networks:\n"
            "• MTN: 024, 053, 054, 055, 059\n"
            "• Vodafone: 020, 050\n"
            "• AirtelTigo: 026, 027, 056, 057\n\n"
            "Please enter a valid phone number:"
        )
        return PHONE
    
    context.user_data['deposit_phone'] = normalized_phone
    context.user_data['deposit_provider'] = network
    
    # Get user data
    user = update.effective_user
    telegram_id = str(user.id)
    amount = context.user_data['deposit_amount']
    
    # Network display names
    network_display = {
        "MTN": "MTN",
        "VODAFONE": "Vodafone",
        "AIRTELTIGO": "AirtelTigo"
    }
    
    # Call backend API
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.BACKEND_API_URL}/api/v1/wallet/deposit/init",
                json={
                    "telegram_id": telegram_id,
                    "amount": float(amount),
                    "phone": normalized_phone,
                    "provider": network
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            display_text = data.get("display_text", "Please approve the mobile money prompt on your phone")
            reference = data.get('reference', 'N/A')

            # Store reference for OTP submission
            context.user_data['deposit_reference'] = reference

            await update.message.reply_text(
                f"✅ Deposit Initiated\n\n"
                f"Detected Network: {network_display.get(network, network)}\n"
                f"Amount: GHS {amount}\n"
                f"Phone: {normalized_phone}\n\n"
                f"{display_text}\n"
                f"Please enter the OTP sent to your phone.\n\n"
                f"Reference: {reference}"
            )

            return OTP
            
    except httpx.HTTPStatusError as e:
        error_msg = "Unknown error"
        try:
            error_data = e.response.json()
            error_msg = error_data.get("detail", "Unknown error")
        except:
            error_msg = str(e)
        
        await update.message.reply_text(
            f"❌ Deposit Failed\n\n"
            f"Error: {error_msg}\n\n"
            "Please try again."
        )
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(
            f"❌ An error occurred: {str(e)}\n\n"
            "Please try again later."
        )
        context.user_data.clear()
        return ConversationHandler.END


async def deposit_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle OTP submission."""
    otp = update.message.text.strip()
    reference = context.user_data.get('deposit_reference')
    
    if not reference:
        await update.message.reply_text(
            "❌ Session expired. Please start deposit again."
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Submit OTP to backend
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.BACKEND_API_URL}/api/v1/wallet/deposit/confirm",
                json={
                    "reference": reference,
                    "otp": otp
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "success":
                await update.message.reply_text(
                    f"✅ {data.get('message', 'Deposit successful!')}"
                )
            else:
                await update.message.reply_text(
                    f"⏳ {data.get('message', 'OTP submitted, waiting for confirmation')}"
                )
            
            context.user_data.clear()
            return ConversationHandler.END
            
    except httpx.HTTPStatusError as e:
        error_msg = "Unknown error"
        try:
            error_data = e.response.json()
            error_msg = error_data.get("detail", "Unknown error")
        except:
            error_msg = str(e)
        
        await update.message.reply_text(
            f"❌ OTP verification failed\n\n"
            f"Error: {error_msg}\n\n"
            "Please try the deposit again."
        )
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(
            f"❌ An error occurred: {str(e)}\n\n"
            "Please try again later."
        )
        context.user_data.clear()
        return ConversationHandler.END


async def deposit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel deposit flow or handle keyboard button."""
    # Clear conversation data
    context.user_data.clear()
    
    # If this is called from a keyboard button fallback, don't show cancel message
    # The button handler will process it
    message_text = update.message.text.strip() if update.message else ""
    keyboard_buttons = ["💼 Balance", "➕ Deposit", "🌐 Bundles", "📜 History", "🎯 Referral", "❓ Help"]
    
    if message_text not in keyboard_buttons:
        # Regular cancel
        await update.message.reply_text(
            "❌ Deposit cancelled."
        )
    
    return ConversationHandler.END