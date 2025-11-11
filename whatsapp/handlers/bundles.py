import httpx
import logging
from decimal import Decimal
from app.core.config import settings
from app.services.user_service import UserService
from app.services.wallet_service import WalletService
from app.services.whatsapp_notifier import WhatsAppNotifierService
from app.utils.phone_utils import normalize_phone_number, validate_phone_number, detect_network
from whatsapp.keyboard import get_network_buttons, get_back_cancel_buttons, get_bundle_list_section, get_bundle_buttons_simple

logger = logging.getLogger(__name__)

# Network display mapping
NETWORK_DISPLAY = {
    "MTN": "MTN",
    "VODAFONE": "Vodafone",
    "AIRTELTIGO": "AirtelTigo"
}


async def start(phone_number: str, bot) -> None:
    """
    Start bundles flow.
    
    Args:
        phone_number: User's phone number
        bot: WhatsAppBot instance
    """
    try:
        normalized_phone = normalize_phone_number(phone_number)
        notifier = WhatsAppNotifierService()

        # Set state to bundles network
        bot.set_user_state(normalized_phone, bot.STATE_BUNDLES_NETWORK)
        
        await notifier.send_interactive_message(
            normalized_phone,
            "🌐 Browse Data Bundles\n\nSelect a network:",
            get_network_buttons()
        )
        
    except Exception as e:
        logger.error(f"Error in bundles start: {str(e)}", exc_info=True)
        await notifier.send_text_message(
            normalized_phone,
            "❌ An error occurred. Please try again later."
        )


async def handle_network(phone_number: str, network: str, bot) -> None:
    """
    Handle network selection.
    
    Args:
        phone_number: User's phone number
        network: Selected network
        bot: WhatsAppBot instance
    """
    try:
        normalized_phone = normalize_phone_number(phone_number)
        notifier = WhatsAppNotifierService()

        # Store network and fetch bundles
        bot.update_user_state_data(normalized_phone, selected_network=network)
        bot.set_user_state(normalized_phone, bot.STATE_BUNDLES_BUNDLE)
        
        # Fetch bundles from backend
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.BACKEND_API_URL}/api/v1/bundles",
                    params={"network": network},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                bundles = data.get("bundles", [])
                
                if not bundles:
                    await bot.send_main_menu(
                        normalized_phone,
                        f"❌ No bundles available for {NETWORK_DISPLAY.get(network, network)}.\n\nPlease try another network or contact admin."
                    )
                    bot.clear_user_state(normalized_phone)
                    return
                
                # Store bundles in state
                bot.update_user_state_data(normalized_phone, bundles=bundles)
                
                # If 3 or fewer bundles, use buttons
                if len(bundles) <= 3:
                    bundle_buttons = get_bundle_buttons_simple(bundles)
                    bundle_buttons.extend(get_back_cancel_buttons())
                    
                    bundle_list_text = "\n".join([
                        f"• {b['capacity']} - GHS {b['price']}"
                        for b in bundles
                    ])
                    
                    await notifier.send_interactive_message(
                        normalized_phone,
                        f"📱 Select a bundle for {NETWORK_DISPLAY.get(network, network)}:\n\n{bundle_list_text}",
                        bundle_buttons
                    )
                else:
                    # Use list message for more bundles
                    section = get_bundle_list_section(bundles, network)
                    back_cancel = get_back_cancel_buttons()
                    
                    # Send list message
                    await notifier.send_list_message(
                        normalized_phone,
                        f"📱 Select a bundle for {NETWORK_DISPLAY.get(network, network)}:",
                        "Select Bundle",
                        [section]
                    )
                    
                    # Also send back/cancel buttons
                    await notifier.send_interactive_message(
                        normalized_phone,
                        "",
                        back_cancel
                    )
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch bundles: {e}")
            await bot.send_main_menu(
                normalized_phone,
                "❌ Failed to fetch bundles. Please try again later."
            )
            bot.clear_user_state(normalized_phone)
        except Exception as e:
            logger.error(f"Error in handle_network: {str(e)}", exc_info=True)
            await notifier.send_text_message(
                normalized_phone,
                "❌ An error occurred. Please try again later."
            )
            bot.clear_user_state(normalized_phone)
            
    except Exception as e:
        logger.error(f"Unexpected error in handle_network: {str(e)}", exc_info=True)
        await bot.notifier.send_text_message(
            normalized_phone,
            "❌ An error occurred. Please try again later."
        )


async def handle_bundle(phone_number: str, bundle_id: str, bot) -> None:
    """
    Handle bundle selection.
    
    Args:
        phone_number: User's phone number
        bundle_id: Selected bundle ID
        bot: WhatsAppBot instance
    """
    try:
        normalized_phone = normalize_phone_number(phone_number)
        notifier = WhatsAppNotifierService()
        state_data = bot.get_user_state(normalized_phone)[1]
        bundles = state_data.get("bundles", [])
        selected_network = state_data.get("selected_network")
        
        # Find selected bundle
        selected_bundle = None
        for bundle in bundles:
            if bundle["id"] == bundle_id:
                selected_bundle = bundle
                break
        
        if not selected_bundle:
            await bot.send_main_menu(
                normalized_phone,
                "❌ Bundle not found. Please try again."
            )
            bot.clear_user_state(normalized_phone)
            return
        
        # Store selected bundle
        bot.update_user_state_data(
            normalized_phone,
            selected_bundle_id=bundle_id,
            selected_bundle=selected_bundle,
            selected_bundle_network=selected_network
        )
        bot.set_user_state(normalized_phone, bot.STATE_BUNDLES_PHONE)
        
        await notifier.send_interactive_message(
            normalized_phone,
            (
                f"📱 Bundle Selected\n\n"
                f"Network: {NETWORK_DISPLAY.get(selected_network, selected_network)}\n"
                f"Capacity: {selected_bundle['capacity']}\n"
                f"Price: GHS {selected_bundle['price']}\n\n"
                f"Please enter the phone number to receive the bundle:\n"
                f"Network: {NETWORK_DISPLAY.get(selected_network, selected_network)}\n"
                f"Example: 0XXXXXXXXX or 233XXXXXXXXX"
            ),
            get_back_cancel_buttons()
        )
        
    except Exception as e:
        logger.error(f"Error in handle_bundle: {str(e)}", exc_info=True)
        await bot.notifier.send_text_message(
            normalized_phone,
            "❌ An error occurred. Please try again later."
        )


async def handle_phone(phone_number: str, phone_input: str, bot) -> None:
    """
    Handle phone number input for bundle purchase.
    
    Args:
        phone_number: User's phone number (WhatsApp user)
        phone_input: Phone number entered by user (to receive bundle)
        bot: WhatsAppBot instance
    """
    try:
        normalized_phone = normalize_phone_number(phone_number)
        notifier = WhatsAppNotifierService()
        state_data = bot.get_user_state(normalized_phone)[1]
        selected_bundle = state_data.get("selected_bundle")
        selected_network = state_data.get("selected_bundle_network")
        
        if not selected_bundle:
            await notifier.send_text_message(
                normalized_phone,
                "❌ Session expired. Please start over."
            )
            bot.clear_user_state(normalized_phone)
            return
        
        # Validate phone format
        is_valid, error_msg = validate_phone_number(phone_input)
        if not is_valid:
            await notifier.send_interactive_message(
                normalized_phone,
                f"❌ {error_msg}\n\nPlease enter a valid phone number:\nExample: 0XXXXXXXXX or 233XXXXXXXXX",
                get_back_cancel_buttons()
            )
            return
        
        # Normalize phone number
        normalized_bundle_phone = normalize_phone_number(phone_input)
        
        # Detect network and validate it matches selected bundle network
        # detect_network can handle both normalized (233XXXXXXXXX) and local (0XXXXXXXXX) formats
        detected_network = detect_network(phone_input)  # Use original input, detect_network handles all formats
        logger.info(f"Network detection: phone_input={phone_input}, normalized={normalized_bundle_phone}, detected_network={detected_network}")
        
        if not detected_network:
            await notifier.send_interactive_message(
                normalized_phone,
                (
                    "❌ Could not detect network from phone number.\n\n"
                    "Supported networks:\n"
                    "• MTN: 024, 053, 054, 055, 059\n"
                    "• Vodafone: 020, 050\n"
                    "• AirtelTigo: 026, 027, 056, 057\n\n"
                    "Please enter a valid phone number:"
                ),
                get_back_cancel_buttons()
            )
            return
        
        # Validate network matches
        if detected_network != selected_network:
            await notifier.send_interactive_message(
                normalized_phone,
                (
                    f"❌ Phone number network ({NETWORK_DISPLAY.get(detected_network, detected_network)}) "
                    f"does not match selected bundle network ({NETWORK_DISPLAY.get(selected_network, selected_network)}).\n\n"
                    f"Please enter a {NETWORK_DISPLAY.get(selected_network, selected_network)} number:"
                ),
                get_back_cancel_buttons()
            )
            return
        
        # Get user from database
        user_service = UserService()
        user = await user_service.get_user_by_whatsapp_phone(normalized_phone)
        
        if not user:
            await notifier.send_text_message(
                normalized_phone,
                "❌ User not found. Please start by typing 'hi'."
            )
            bot.clear_user_state(normalized_phone)
            return
        
        # Check balance before creating order
        wallet_service = WalletService()
        bundle_price = Decimal(str(selected_bundle['price']))
        
        try:
            balance = await wallet_service.get_balance(user["id"])
            logger.info(f"Balance check: user_id={user['id']}, balance={balance}, bundle_price={bundle_price}")
            
            if balance < bundle_price:
                # Insufficient balance - return to main menu
                await bot.send_main_menu(
                    normalized_phone,
                    (
                        f"❌ Insufficient balance.\n\n"
                        f"Account balance is GHS {balance}, Required GHS {bundle_price} to buy {selected_bundle['capacity']}GB bundle."
                    )
                )
                # Clear state to allow user to start fresh
                bot.clear_user_state(normalized_phone)
                return
        except Exception as e:
            logger.error(f"Error checking balance: {str(e)}", exc_info=True)
            await bot.send_main_menu(
                normalized_phone,
                "❌ Error checking balance. Please try again later."
            )
            bot.clear_user_state(normalized_phone)
            return
        
        # Create order via backend API
        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"Creating order: user_id={user['id']}, bundle_id={selected_bundle['id']}, phone={normalized_bundle_phone}")
                
                response = await client.post(
                    f"{settings.BACKEND_API_URL}/api/v1/orders",
                    json={
                        "user_id": str(user["id"]),  # Pass user_id directly for WhatsApp
                        "bundle_id": selected_bundle["id"],
                        "phone": normalized_bundle_phone
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                logger.info(f"Order creation response: {data}")
                
                if data.get("status") == "success":
                    order = data.get("order", {})
                    vendor_ref = order.get("vendor_reference", "N/A")
                    
                    await bot.send_main_menu(
                        normalized_phone,
                        (
                            f"✅ Order Created Successfully!\n\n"
                            f"Bundle: {selected_bundle['capacity']}\n"
                            f"Network: {NETWORK_DISPLAY.get(selected_network, selected_network)}\n"
                            f"Phone: {normalized_bundle_phone}\n"
                            f"Price: GHS {selected_bundle['price']}\n"
                            f"Status: {order.get('status', 'pending')}\n\n"
                            f"Vendor Reference: {vendor_ref}\n\n"
                            f"Your bundle will be delivered shortly. You can check your order status in History."
                        )
                    )
                else:
                    error_msg = data.get("message", "Unknown error")
                    await bot.send_main_menu(
                        normalized_phone,
                        f"❌ Order Failed\n\nPlease try again OR contact support if issue persists."
                    )
                
                bot.clear_user_state(normalized_phone)
                
        except httpx.HTTPStatusError as e:
            error_msg = "Unknown error"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("detail", "Unknown error")
            except:
                error_msg = str(e)
            
            logger.error(f"Order creation failed: {error_msg}")
            await bot.send_main_menu(
                normalized_phone,
                f"❌ Order Failed\n\nPlease try again OR contact support if issue persists."
            )
            bot.clear_user_state(normalized_phone)
        except Exception as e:
            logger.error(f"Error in handle_phone: {str(e)}", exc_info=True)
            await notifier.send_text_message(
                normalized_phone,
                "❌ An error occurred. Please try again later."
            )
            bot.clear_user_state(normalized_phone)
            
    except Exception as e:
        logger.error(f"Unexpected error in handle_phone: {str(e)}", exc_info=True)
        await bot.notifier.send_text_message(
            normalized_phone,
            "❌ An error occurred. Please try again later."
        )
        bot.clear_user_state(normalized_phone)

