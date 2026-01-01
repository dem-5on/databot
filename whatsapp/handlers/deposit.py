import httpx
import asyncio
import logging
from decimal import Decimal
from app.core.config import settings
from app.services.whatsapp_notifier import WhatsAppNotifierService
from whatsapp.keyboard import get_back_cancel_buttons
from app.utils.phone_utils import normalize_phone_number
from app.utils.backend_client import BackendAPIClient

logger = logging.getLogger(__name__)

# Network prefix mapping
NETWORK_PREFIXES = {
    "MTN": ["024", "054", "055", "059", "053"],
    "TELECEL": ["020", "050"],
    "AIRTELTIGO": ["027", "057", "026", "056"]
}


def normalize_phone_for_detection(phone: str) -> str:
    """
    Normalize phone number to 0XXXXXXXXX format for network detection.
    
    Args:
        phone: Phone number in any format
        
    Returns:
        Normalized phone number starting with 0
    """
    phone = phone.strip().replace(" ", "").replace("-", "")
    
    # If starts with +233, remove +
    if phone.startswith("+233"):
        phone = phone[1:]
    
    # If starts with 233, convert to 0 format
    if phone.startswith("233") and len(phone) == 12:
        phone = "0" + phone[3:]
    
    return phone


def detect_network(phone: str) -> str | None:
    """
    Detect mobile network from phone number prefix.
    Phone should be in 0XXXXXXXXX format.
    
    Args:
        phone: Phone number (should be normalized to 0XXXXXXXXX first)
        
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
    
    # Check if it's 13 digits starting with +233
    if phone.startswith("+233") and len(phone) == 13 and phone[1:].isdigit():
        return True, ""
    
    return False, "Invalid format. Use 0XXXXXXXXX or 233XXXXXXXXX"


async def start(phone_number: str, bot) -> None:
    """
    Start deposit flow.
    
    Args:
        phone_number: User's phone number
        bot: WhatsAppBot instance
    """
    try:
        normalized_phone = normalize_phone_number(phone_number)
        notifier = WhatsAppNotifierService()

        # Set state to deposit amount
        bot.set_user_state(normalized_phone, bot.STATE_DEPOSIT_AMOUNT)
        
        await notifier.send_interactive_message(
            normalized_phone,
            (
                "➕ Deposit Funds\n\n"
                "Please enter the amount you want to deposit (GHS):\n"
                "Example: 50.00\n\n"
            ),
            get_back_cancel_buttons()
        )
        
    except Exception as e:
        logger.error(f"Error in deposit start: {str(e)}", exc_info=True)
        await bot.notifier.send_text_message(
            normalized_phone,
            "❌ An error occurred. Please try again later."
        )


async def handle_amount(phone_number: str, amount_text: str, bot) -> None:
    """
    Handle deposit amount input.
    
    Args:
        phone_number: User's phone number
        amount_text: Amount entered by user
        bot: WhatsAppBot instance
    """
    try:
        normalized_phone = normalize_phone_number(phone_number)
        notifier = WhatsAppNotifierService()
        
        logger.info(f"Handling amount for {normalized_phone}: {amount_text}")
        
        # Validate amount
        try:
            amount = Decimal(amount_text.strip())
            if amount < settings.MINIMUM_DEPOSIT_AMOUNT:
                await notifier.send_interactive_message(
                    normalized_phone,
                    f"❌ Minimum deposit amount is GHS {settings.MINIMUM_DEPOSIT_AMOUNT}. Please enter a valid amount:",
                    get_back_cancel_buttons()
                )
                return
            
            # Store amount and move to phone input state
            # Update data first, then change state (set_user_state will preserve the updated data)
            bot.update_user_state_data(normalized_phone, deposit_amount=str(amount))
            bot.set_user_state(normalized_phone, bot.STATE_DEPOSIT_PHONE)
            
            # Verify state was saved
            verify_state, verify_data = bot.get_user_state(normalized_phone)
            logger.info(f"State after saving amount for {normalized_phone}: state={verify_state}, data={verify_data}")
            
            await notifier.send_interactive_message(
                normalized_phone,
                (
                    f"📱 Amount: GHS {amount}\n\n"
                    "Please enter your phone number:\n"
                    "Example: 0XXXXXXXXX or 233XXXXXXXXX"
                ),
                get_back_cancel_buttons()
            )
            
        except (ValueError, TypeError):
            await notifier.send_interactive_message(
                normalized_phone,
                "❌ Invalid amount. Please enter a valid number (e.g., 50):",
                get_back_cancel_buttons()
            )
            
    except Exception as e:
        logger.error(f"Error in handle_amount: {str(e)}", exc_info=True)
        await notifier.send_text_message(
            normalized_phone,
            "❌ An error occurred. Please try again later."
        )


async def handle_phone(phone_number: str, phone_input: str, bot) -> None:
    """
    Handle deposit phone input.
    
    Args:
        phone_number: User's phone number (WhatsApp user)
        phone_input: Phone number entered by user (for mobile money)
        bot: WhatsAppBot instance
    """
    try:
        normalized_phone = normalize_phone_number(phone_number)
        notifier = WhatsAppNotifierService()
        
        # Get state data
        state_info = bot.get_user_state(normalized_phone)
        if not state_info or len(state_info) < 2:
            logger.error(f"No state data found for {normalized_phone}")
            await notifier.send_text_message(
                normalized_phone,
                "❌ Session expired. Please start deposit again by typing 'deposit'."
            )
            bot.clear_user_state(normalized_phone)
            return
        
        state_data = state_info[1]
        amount = state_data.get("deposit_amount")
        
        # Debug logging
        logger.info(f"State data for {normalized_phone}: {state_data}")
        logger.info(f"Amount retrieved: {amount}")
        
        if not amount:
            logger.error(f"No amount found in state data for {normalized_phone}")
            await notifier.send_text_message(
                normalized_phone,
                "❌ Session expired. Please start deposit again by typing 'deposit'."
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
        
        # Normalize phone for detection (to 0XXXXXXXXX format)
        phone_for_detection = normalize_phone_for_detection(phone_input)
        
        # Add debug logging
        logger.info(f"Original phone input: {phone_input}")
        logger.info(f"Phone for detection: {phone_for_detection}")
        
        # Detect network
        network = detect_network(phone_for_detection)
        logger.info(f"Detected network: {network}")
        
        if not network:
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
        
        # Normalize phone for API (to 233XXXXXXXXX format - what your backend expects)
        normalized_momo_phone = normalize_phone_number(phone_input)
        
        # Store phone and network
        bot.update_user_state_data(
            normalized_phone,
            deposit_phone=normalized_momo_phone,
            deposit_provider=network
        )
        
        # Get user from database
        from app.services.user_service import UserService
        user_service = UserService()
        user = await user_service.get_user_by_whatsapp_phone(normalized_phone)
        
        if not user:
            await notifier.send_text_message(
                normalized_phone,
                "❌ User not found. Please start by typing 'hi' / 'start'."
            )
            return
        
        # Network display names
        network_display = {
            "MTN": "MTN",
            "TELECEL": "Telecel",
            "AIRTELTIGO": "AirtelTigo"
        }
        
        # Call backend API to initialize deposit with retry logic
        try:
            logger.info(f"Initializing deposit: user_id={user['id']}, amount={amount}, phone={normalized_momo_phone}, provider={network}")
            
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    client = BackendAPIClient.get_client()
                    response = await client.post(
                        f"{settings.BACKEND_API_URL}/api/v1/wallet/deposit/init",
                        json={
                            "user_id": str(user["id"]),  # Pass user_id directly for WhatsApp
                            "amount": float(amount),
                            "phone": normalized_momo_phone,
                            "provider": network
                        },
                    )
                    response.raise_for_status()
                    break  # Success
                except (httpx.RemoteProtocolError, httpx.ConnectError) as conn_error:
                    if attempt < max_retries:
                        logger.warning(f"Connection error (attempt {attempt + 1}/{max_retries + 1}), resetting client")
                        await BackendAPIClient.reset_client()
                    else:
                        raise
            
            data = response.json()
            
            logger.info(f"Deposit init response: {data}")
            
            # Get display_text from nested response structure
            paystack_response = data.get("paystack_response", {})
            paystack_data = paystack_response.get("data", {})
            display_text = paystack_data.get("display_text") or data.get("display_text") or "Please approve the mobile money prompt on your phone."
            reference = data.get('reference', 'N/A')
            
            if not reference or reference == 'N/A':
                logger.error(f"Missing reference in deposit init response: {data}")
                raise ValueError("Failed to get transaction reference from server")
            
            # Store reference and move to OTP state
            bot.update_user_state_data(normalized_phone, deposit_reference=reference)
            bot.set_user_state(normalized_phone, bot.STATE_DEPOSIT_OTP)
            
            await notifier.send_interactive_message(
                normalized_phone,
                (
                    f"✅ Deposit Initiated\n\n"
                    f"Detected Network: {network_display.get(network, network)}\n"
                    f"Amount: GHS {amount}\n"
                    f"Phone: {normalized_momo_phone}\n\n"
                    f"{display_text}\n\n"
                    f"OR\n"
                    f"Go to my approvals on your mobile device to approve the payment.\n\n"
                    f"Please enter the OTP sent to your phone."
                ),
                get_back_cancel_buttons()
            )
                
        except httpx.HTTPStatusError as e:
            error_msg = "Unknown error"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("detail", "Unknown error")
            except Exception as json_error:
                logger.warning(f"Failed to parse error response JSON: {json_error}")
                error_msg = str(e)
            
            logger.error(f"Deposit init failed: {error_msg}")
            await notifier.send_interactive_message(
                normalized_phone,
                f"❌ Deposit Failed\n\nPlease try again.",
                get_back_cancel_buttons()
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


async def handle_otp(phone_number: str, otp: str, bot) -> None:
    """
    Handle deposit OTP submission.
    
    Args:
        phone_number: User's phone number
        otp: OTP entered by user
        bot: WhatsAppBot instance
    """
    try:
        normalized_phone = normalize_phone_number(phone_number)
        notifier = WhatsAppNotifierService()
        state_data = bot.get_user_state(normalized_phone)[1]
        reference = state_data.get("deposit_reference")
        
        if not reference:
            await notifier.send_text_message(
                normalized_phone,
                "❌ Session expired. Please start deposit again."
            )
            bot.clear_user_state(normalized_phone)
            return
        
        # Submit OTP to backend with retry logic
        try:
            logger.info(f"Submitting OTP for reference: {reference}")
            
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    client = BackendAPIClient.get_client()
                    response = await client.post(
                        f"{settings.BACKEND_API_URL}/api/v1/wallet/deposit/confirm",
                        json={
                            "reference": reference,
                            "otp": otp.strip()
                        },
                    )
                    response.raise_for_status()
                    break  # Success
                except (httpx.RemoteProtocolError, httpx.ConnectError) as conn_error:
                    if attempt < max_retries:
                        logger.warning(f"Connection error (attempt {attempt + 1}/{max_retries + 1}), resetting client")
                        await BackendAPIClient.reset_client()
                    else:
                        raise
            
            data = response.json()
            
            logger.info(f"OTP submission response: {data}")
            
            if data.get("status") == "success":
                # Payment successful immediately
                await bot.send_main_menu(
                    normalized_phone,
                    f"✅ {data.get('message', 'Deposit successful! Your wallet has been credited.')}"
                )
                bot.clear_user_state(normalized_phone)
                return
            else:
                # OTP submitted but payment pending - verify immediately
                await notifier.send_text_message(
                    normalized_phone,
                    "⏳ OTP submitted. Verifying payment status..."
                )
                
                # Wait a moment for Paystack to process
                await asyncio.sleep(2)
                
                # Try to verify the transaction
                try:
                    logger.info(f"Verifying transaction: {reference}")
                    client = BackendAPIClient.get_client()
                    verify_response = await client.post(
                        f"{settings.BACKEND_API_URL}/api/v1/wallet/deposit/verify/{reference}",
                    )
                    verify_response.raise_for_status()
                    verify_data = verify_response.json()
                    
                    logger.info(f"Verification response: {verify_data}")
                    
                    if verify_data.get("status") == "success":
                        # Get balance info if available
                        transaction = verify_data.get("transaction", {})
                        wallet_info = ""
                        if transaction:
                            raw_payload = transaction.get("raw_payload", {})
                            if isinstance(raw_payload, dict):
                                new_balance = raw_payload.get("new_balance")
                                if new_balance:
                                    wallet_info = f"\n\n💰 New Balance: GHS {new_balance}"
                        
                        await bot.send_main_menu(
                            normalized_phone,
                            f"✅ Deposit verified and wallet credited!{wallet_info}\n\nYour wallet has been updated with the deposit amount."
                        )
                    elif verify_data.get("status") == "pending":
                        # Still pending - check again after a short delay
                        await asyncio.sleep(3)
                        
                        # Second verification attempt
                        try:
                            client = BackendAPIClient.get_client()
                            verify_response2 = await client.post(
                                f"{settings.BACKEND_API_URL}/api/v1/wallet/deposit/verify/{reference}",
                            )
                            verify_response2.raise_for_status()
                            verify_data2 = verify_response2.json()
                            
                            if verify_data2.get("status") == "success":
                                transaction = verify_data2.get("transaction", {})
                                wallet_info = ""
                                if transaction:
                                    raw_payload = transaction.get("raw_payload", {})
                                    if isinstance(raw_payload, dict):
                                        new_balance = raw_payload.get("new_balance")
                                        if new_balance:
                                            wallet_info = f"\n\n💰 New Balance: GHS {new_balance}"
                                
                                await bot.send_main_menu(
                                    normalized_phone,
                                    f"✅ Payment verified! Your wallet has been credited.{wallet_info}"
                                )
                            else:
                                await bot.send_main_menu(
                                    normalized_phone,
                                    (
                                        "⏳ Payment is still being processed.\n\n"
                                        "If your payment was successful, your wallet will be credited shortly.\n"
                                        "You can check your balance using the 💼 Balance button."
                                    )
                                )
                        except Exception:
                            await bot.send_main_menu(
                                normalized_phone,
                                (
                                    "⏳ Payment is being processed.\n\n"
                                    "If your payment was successful, your wallet will be credited shortly.\n"
                                    "You can check your balance using the 💼 Balance button."
                                )
                            )
                    else:
                        await bot.send_main_menu(
                            normalized_phone,
                            (
                                f"⚠️ Payment status: {verify_data.get('paystack_status', 'unknown')}\n\n"
                                "Please check your balance. If the payment was successful but balance wasn't updated, "
                                "please contact support."
                            )
                        )
                except Exception as verify_error:
                    logger.error(f"Verification error: {verify_error}", exc_info=True)
                    await bot.send_main_menu(
                        normalized_phone,
                        (
                            "⏳ OTP submitted successfully.\n\n"
                            "Payment is being processed. If your payment was successful, "
                            "your wallet will be credited shortly via webhook.\n\n"
                            "You can check your balance using the 💼 Balance button."
                        )
                    )
            
            bot.clear_user_state(normalized_phone)
                
        except httpx.HTTPStatusError as e:
            error_msg = "Unknown error"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("detail", "Unknown error")
            except Exception as json_error:
                logger.warning(f"Failed to parse error response JSON: {json_error}")
                error_msg = str(e)
            
            logger.error(f"OTP verification failed: {error_msg}")
            await bot.send_main_menu(
                normalized_phone,
                f"❌ OTP verification failed\n\nPlease try the deposit again."
            )
            bot.clear_user_state(normalized_phone)
        except Exception as e:
            logger.error(f"Error in handle_otp: {str(e)}", exc_info=True)
            await notifier.send_text_message(
                normalized_phone,
                "❌ An error occurred. Please try again later."
            )
            bot.clear_user_state(normalized_phone)
            
    except Exception as e:
        logger.error(f"Unexpected error in handle_otp: {str(e)}", exc_info=True)
        await notifier.send_text_message(
            normalized_phone,
            "❌ An error occurred, Please enter the correct OTP or try again later."
        )
        bot.clear_user_state(normalized_phone)