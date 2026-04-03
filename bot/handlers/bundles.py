import httpx
import logging
from telegram import Update
from app.core.config import settings
from app.utils.backend_client import BackendAPIClient
from telegram.ext import ContextTypes, ConversationHandler
from app.utils.phone_utils import validate_phone_number, detect_network, normalize_phone_to_local
from bot.keyboard import get_network_keyboard, get_bundles_keyboard, get_phone_input_keyboard
from bot.api_client import get_auth_headers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states
BUNDLES_NETWORK, BUNDLES_BUNDLE, BUNDLES_PHONE = range(3)

# Network display mapping
NETWORK_DISPLAY = {
    "MTN": "MTN",
    "TELECEL": "Telecel",
    "AIRTELTIGO": "AirtelTigo"
}

# Network prefix mapping for phone validation (for display purposes)
NETWORK_PREFIXES = {
    "MTN": ["024", "054", "055", "059", "053"],
    "TELECEL": ["020", "050"],
    "AIRTELTIGO": ["027", "057", "026", "056"]
}




async def bundles_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start bundles flow."""
    await update.message.reply_text(
        "🌐 Browse Data Bundles\n\n"
        "Select a network:",
        reply_markup=get_network_keyboard()
    )
    return BUNDLES_NETWORK


async def bundles_network(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle network selection."""
    query = update.callback_query
    await query.answer()
    
    # Handle cancel
    if query.data == "cancel:bundles":
        await bundles_cancel_callback(update, context)
        return ConversationHandler.END
    
    network = query.data.split(":")[1]
    context.user_data['selected_network'] = network
    
    # Fetch bundles from backend
    try:
        client = BackendAPIClient.get_client()
        response = await client.get(
            f"{settings.BACKEND_API_URL}/api/v1/bundles",
            params={"network": network},
            timeout=10.0
        )
        response.raise_for_status()
        data = response.json()
        bundles = data.get("bundles", [])
        
        if not bundles:
            await query.edit_message_text(
                f"❌ No bundles available for {NETWORK_DISPLAY.get(network, network)}.\n\n"
                "Please try another network or contact admin."
            )
            context.user_data.clear()
            return ConversationHandler.END
        
        # Create keyboard with bundles
        keyboard = get_bundles_keyboard(bundles)
        
        await query.edit_message_text(
            f"📱 Select a bundle for {NETWORK_DISPLAY.get(network, network)}:\n\n",
            reply_markup=keyboard
        )
        
        # Store bundles in context for later use
        context.user_data['bundles'] = bundles
        
        return BUNDLES_BUNDLE
        
    except Exception as e:
        await query.edit_message_text(
            f"❌ Error fetching bundles: {str(e)}\n\n"
            "Please try again later."
        )
        context.user_data.clear()
        return ConversationHandler.END


async def bundles_bundle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bundle selection."""
    query = update.callback_query
    await query.answer()
    
    # Handle back to networks
    if query.data == "back:networks":
        await query.edit_message_text(
            "🌐 Browse Data Bundles\n\n"
            "Select a network:",
            reply_markup=get_network_keyboard()
        )
        return BUNDLES_NETWORK
    
    # Handle cancel
    if query.data == "cancel:bundles":
        await bundles_cancel_callback(update, context)
        return ConversationHandler.END
    
    # Handle back to bundles (from phone input)
    if query.data == "back:bundles":
        # Get the selected network
        network = context.user_data.get('selected_network')
        bundles = context.user_data.get('bundles', [])
        
        if network and bundles:
            keyboard = get_bundles_keyboard(bundles)
            await query.edit_message_text(
                f"📱 Select a bundle for {NETWORK_DISPLAY.get(network, network)}:\n\n",
                reply_markup=keyboard
            )
            return BUNDLES_BUNDLE
        else:
            # If context lost, go back to networks
            await query.edit_message_text(
                "🌐 Browse Data Bundles\n\n"
                "Select a network:",
                reply_markup=get_network_keyboard()
            )
            return BUNDLES_NETWORK
    
    bundle_id = query.data.split(":")[1]
    context.user_data['selected_bundle_id'] = bundle_id
    
    # Find bundle details
    bundles = context.user_data.get('bundles', [])
    selected_bundle = next((b for b in bundles if b['id'] == bundle_id), None)
    
    if selected_bundle:
        # Store the bundle's network for validation
        bundle_network = selected_bundle.get('network', context.user_data.get('selected_network', ''))
        context.user_data['selected_bundle_network'] = bundle_network
        
        bundle_info = (
            f"📦 Bundle Selected:\n"
            f"Network: {NETWORK_DISPLAY.get(bundle_network, bundle_network)}\n"
            f"Size: {selected_bundle['capacity']}GB\n"
            f"Price: GHS {selected_bundle['price']}\n\n"
        )
    else:
        bundle_info = ""
        bundle_network = context.user_data.get('selected_network', '')
        context.user_data['selected_bundle_network'] = bundle_network
    
    await query.edit_message_text(
        f"{bundle_info}📱 Enter the phone number to receive the data bundle:\n"
        f"⚠️ <b>Important:</b> The phone number must be a {NETWORK_DISPLAY.get(bundle_network, bundle_network)} number.\n\n",
        reply_markup=get_phone_input_keyboard(),
        parse_mode="HTML"
    )
    return BUNDLES_PHONE

async def bundles_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle phone input for bundle purchase."""
    # Check if this is a callback query (back/cancel button)
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        if query.data == "back:bundles":
            # Get the selected network
            network = context.user_data.get('selected_network')
            bundles = context.user_data.get('bundles', [])
            
            if network and bundles:
                keyboard = get_bundles_keyboard(bundles)
                await query.edit_message_text(
                    f"📱 Select a bundle for {NETWORK_DISPLAY.get(network, network)}:\n\n",
                    reply_markup=keyboard
                )
                return BUNDLES_BUNDLE
            else:
                # If context lost, go back to networks
                await query.edit_message_text(
                    "🌐 Browse Data Bundles\n\n"
                    "Select a network:",
                    reply_markup=get_network_keyboard()
                )
                return BUNDLES_NETWORK
        
        elif query.data == "cancel:bundles":
            await bundles_cancel_callback(update, context)
            return ConversationHandler.END
        
        return BUNDLES_PHONE
    
    # Handle text input (phone number)
    phone = update.message.text.strip()
    
    # Validate phone format
    is_valid, error_msg = validate_phone_number(phone)
    if not is_valid:
        bundle_network = context.user_data.get('selected_bundle_network', context.user_data.get('selected_network', ''))
        await update.message.reply_text(
            f"❌ {error_msg}\n\n"
            f"Please enter a valid phone number for {NETWORK_DISPLAY.get(bundle_network, bundle_network)}:\n"
            "Example: 0XXXXXXXXX or 233XXXXXXXXX\n\n"
            "Or use the buttons below to go back or cancel.",
            reply_markup=get_phone_input_keyboard()
        )
        return BUNDLES_PHONE
    
    # Normalize phone number to local format (0XXXXXXXXX)
    normalized_phone = normalize_phone_to_local(phone)
    
    # Get the selected bundle's network
    bundle_network = context.user_data.get('selected_bundle_network', context.user_data.get('selected_network', ''))
    
    # Detect network from phone number
    phone_network = detect_network(normalized_phone)
    
    if not phone_network:
        await update.message.reply_text(
            f"❌ Could not detect network from phone number.\n\n"
            f"⚠️ <b>Important:</b> The phone number must be a {NETWORK_DISPLAY.get(bundle_network, bundle_network)} number.\n\n"
            "Supported network prefixes:\n"
            "• MTN: 024, 053, 054, 055, 059\n"
            "• Vodafone: 020, 050\n"
            "• AirtelTigo: 026, 027, 056, 057\n\n"
            "Please enter a valid phone number:",
            reply_markup=get_phone_input_keyboard(),
            parse_mode="HTML"
        )
        return BUNDLES_PHONE
    
    # Validate that phone network matches bundle network
    if phone_network != bundle_network:
        bundle_display = NETWORK_DISPLAY.get(bundle_network, bundle_network)
        phone_display = NETWORK_DISPLAY.get(phone_network, phone_network)
        
        await update.message.reply_text(
            f"❌ <b>Network Mismatch!</b>\n\n"
            f"You selected a <b>{bundle_display}</b> bundle, but the phone number ({normalized_phone}) is a <b>{phone_display}</b> number.\n\n"
            f"⚠️ Please enter a <b>{bundle_display}</b> phone number to receive this bundle.\n\n"
            f"{get_network_prefixes_text(bundle_network)}\n\n"
            "Or use the buttons below to go back and select a different bundle.",
            reply_markup=get_phone_input_keyboard(),
            parse_mode="HTML"
        )
        return BUNDLES_PHONE
    
    # Phone number is valid and matches bundle network
    bundle_id = context.user_data.get('selected_bundle_id')
    await create_order_from_bundle(update, context, bundle_id, normalized_phone)
    return ConversationHandler.END


def get_network_prefixes_text(network: str) -> str:
    """Get formatted text showing network prefixes."""
    prefixes = NETWORK_PREFIXES.get(network, [])
    return " • " + ", ".join(prefixes) if prefixes else "Unknown"



async def create_order_from_bundle(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    bundle_id: str,
    phone: str
):
    """Create order from selected bundle."""
    user = update.effective_user
    telegram_id = str(user.id)
    
    try:
        client = BackendAPIClient.get_client()
        headers = get_auth_headers(telegram_id, "telegram")
        response = await client.post(
            f"{settings.BACKEND_API_URL}/api/v1/orders",
            json={
                "telegram_id": telegram_id,
                "bundle_id": bundle_id,
                "phone": phone
            },
            headers=headers,
            timeout=60.0
        )
        response.raise_for_status()
        data = response.json()
        
        if isinstance(update, Update) and update.message:
            await update.message.reply_text(
                f"✅ Order Created Successfully!\n\n"
                f"Order ID: {data.get('order_id', 'N/A')}\n"
                f"Status: {data.get('order_status', 'N/A')}\n"
                f"Vendor Reference: {data.get('vendor_reference', 'N/A')}\n\n"
                f"Your data bundle will be delivered shortly."
            )
        else:
            query = update.callback_query
            await query.edit_message_text(
                f"✅ Order Created Successfully!\n\n"
                f"Order ID: {data.get('order_id', 'N/A')}\n"
                f"Status: {data.get('order_status', 'N/A')}\n"
                f"Vendor Reference: {data.get('vendor_reference', 'N/A')}\n\n"
                f"Your data bundle will be delivered shortly."
            )
        
        context.user_data.clear()
            
    except httpx.HTTPStatusError as e:
        error_msg = "Unknown error"
        try:
            error_data = e.response.json()
            error_msg = error_data.get("detail", "Unknown error")
            # Log the full error for debugging
            logger.error(f"Order creation failed: {e.response.status_code} - {error_msg}")
            logger.error(f"Request data: telegram_id={telegram_id}, bundle_id={bundle_id}, phone={phone}")
        except Exception as parse_error:
            error_msg = f"HTTP {e.response.status_code}: {str(e)}"
            logger.error(f"Failed to parse error response: {parse_error}")

        try:
            if update.message:
                await update.message.reply_text(
                    f"❌ Order Failed\n\n"
                    f"{error_msg}\n\n"
                    "Please try again."
                )
            elif update.callback_query:
                query = update.callback_query
                await query.edit_message_text(
                    f"❌ Order Failed\n\n"
                    f"{error_msg}\n\n"
                    "Please try again."
                )
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")
        finally:
            context.user_data.clear()
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Unexpected error in order creation: {error_msg}")
        logger.error(f"Request data: telegram_id={telegram_id}, bundle_id={bundle_id}, phone={phone}")

        try:
            if update.message:
                await update.message.reply_text(
                    f"❌ An error occurred: {error_msg}\n\n"
                    "Please try again later."
                )
            elif update.callback_query:
                query = update.callback_query
                await query.edit_message_text(
                    f"❌ An error occurred: {error_msg}\n\n"
                    "Please try again later."
                )
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")
        finally:
            context.user_data.clear()


async def bundles_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel bundles flow (from /cancel command)."""
    context.user_data.clear()
    if update.message:
        await update.message.reply_text(
            "❌ Bundle selection cancelled."
        )
    return ConversationHandler.END


async def bundles_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel bundles flow (from callback button)."""
    context.user_data.clear()
    query = update.callback_query
    if query:
        await query.edit_message_text(
            "❌ Bundle selection cancelled.\n\n"
            "Use 🌐 Bundles to start again."
        )

