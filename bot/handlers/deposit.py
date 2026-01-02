import httpx
import logging
import asyncio
from decimal import Decimal
from telegram import Update
from app.core.config import settings
from telegram.ext import ContextTypes, ConversationHandler
from app.utils.phone_utils import validate_phone_number, detect_network, normalize_phone_to_local
from app.utils.backend_client import BackendAPIClient

logger = logging.getLogger(__name__)

# Conversation states
AMOUNT, PHONE, OTP = range(3)

# Network prefix mapping (for display purposes)
NETWORK_PREFIXES = {
    "MTN": ["024", "054", "055", "059", "053"],
    "TELECEL": ["020", "050"],
    "AIRTELTIGO": ["027", "057", "026", "056"]
}



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
        # Get dynamic deposit limits
        from app.services.settings_service import SettingsService
        settings_service = SettingsService()
        min_deposit = await settings_service.get_min_deposit_amount()
        max_deposit = await settings_service.get_max_deposit_amount()

        amount = Decimal(update.message.text.strip())
        
        if amount < min_deposit:
            await update.message.reply_text(
                f"❌ Minimum deposit amount is GHS {min_deposit}. Please enter a valid amount:"
            )
            return AMOUNT
        
        if amount > max_deposit:
            await update.message.reply_text(
                f"❌ Maximum deposit amount is GHS {max_deposit}. Please enter a valid amount:"
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
    normalized_phone = normalize_phone_to_local(phone)
    
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
        "TELECEL": "Telecel",
        "AIRTELTIGO": "AirtelTigo"
    }
    
    # Call backend API
    try:
        headers = BackendAPIClient.get_auth_headers(telegram_id, "telegram")
        logger.info(f"Initializing deposit: telegram_id={telegram_id}, amount={amount}, phone={normalized_phone}, provider={network}")
        
        # Retry logic for connection errors
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                client = BackendAPIClient.get_client()
                response = await client.post(
                    f"{settings.BACKEND_API_URL}/api/v1/wallet/deposit/init",
                    json={
                        "telegram_id": telegram_id,
                        "amount": float(amount),
                        "phone": normalized_phone,
                        "provider": network
                    },
                    headers=headers,
                )
                
                logger.info(f"Deposit init response status: {response.status_code}")
                
                response.raise_for_status()
                break  # Success
            except (httpx.RemoteProtocolError, httpx.ConnectError) as conn_error:
                if attempt < max_retries:
                    logger.warning(f"Connection error (attempt {attempt + 1}/{max_retries + 1}), resetting client")
                    await BackendAPIClient.reset_client()
                else:
                    raise
        
        data = response.json()
        
        logger.info(f"Deposit init response data: {data}")
        
        # Get display_text from nested response structure
        paystack_response = data.get("paystack_response", {})
        paystack_data = paystack_response.get("data", {})
        display_text = paystack_data.get("display_text") or data.get("display_text") or "Please approve the mobile money prompt on your phone ."
        reference = data.get('reference', 'N/A')
        
        if not reference or reference == 'N/A':
            logger.error(f"Missing reference in deposit init response: {data}")
            raise ValueError("Failed to get transaction reference from server")

        # Store reference for OTP submission
        context.user_data['deposit_reference'] = reference

        # Try to send confirmation message, but don't fail if Telegram API times out
        try:
            await update.message.reply_text(
                f"✅ Deposit Initiated\n\n"
                f"Detected Network: {network_display.get(network, network)}\n"
                f"Amount: GHS {amount}\n"
                f"Phone: {normalized_phone}\n\n"
                f"{display_text}\n\n"
                f"OR\n"
                f"Go to my approvals on your mobile device to approve the payment.\n\n"
            )
        except Exception as telegram_error:
            # Log the error but don't fail - the deposit was successful
            logger.error(f"Failed to send Telegram message (deposit was successful): {telegram_error}")
        return OTP
            
    except httpx.HTTPStatusError as e:
        error_msg = "Unknown error"
        try:
            error_data = e.response.json()
            error_msg = error_data.get("detail", "Unknown error")
        except Exception as json_error:
            logger.warning(f"Failed to parse error response JSON: {json_error}")
            error_msg = str(e)
        
        logger.error(f"Deposit init failed with HTTP error: {error_msg}")
        
        # Try to send error message, but handle Telegram API errors gracefully
        try:
            await update.message.reply_text(
                f"❌ Deposit Failed\n\n"
                "Please try again."
            )
        except Exception as telegram_error:
            logger.error(f"Failed to send error message via Telegram: {telegram_error}")
            # Try to send via edit if this was a callback query
            try:
                if update.callback_query:
                    await update.callback_query.edit_message_text(
                        f"❌ Deposit Failed\n\n"
                        "Please try again."
                    )
            except Exception:
                pass
        
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Unexpected error in deposit_phone: {e}", exc_info=True)
        
        # Try to send error message, but handle Telegram API errors gracefully
        try:
            await update.message.reply_text(
                f"❌ An error occurred: {str(e)}\n\n"
                "Please try again later."
            )
        except Exception as telegram_error:
            logger.error(f"Failed to send error message via Telegram: {telegram_error}")
            # Try to send via edit if this was a callback query
            try:
                if update.callback_query:
                    await update.callback_query.edit_message_text(
                        f"❌ An error occurred\n\n"
                        "Please try again later."
                    )
            except Exception:
                pass  # Give up on sending error message
        
        context.user_data.clear()
        return ConversationHandler.END


async def deposit_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle OTP submission with immediate verification."""
   
    
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
        user = update.effective_user
        telegram_id = str(user.id)
        headers = BackendAPIClient.get_auth_headers(telegram_id, "telegram")
        
        logger.info(f"Submitting OTP for reference: {reference}")
        
        # Retry logic for connection errors
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                client = BackendAPIClient.get_client()
                response = await client.post(
                    f"{settings.BACKEND_API_URL}/api/v1/wallet/deposit/confirm",
                    json={
                        "reference": reference,
                        "otp": otp
                    },
                    headers=headers,
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
            # Payment successful immediately - notify user
            try:
                await update.message.reply_text(
                    f"✅ {data.get('message', 'Deposit successful! Your wallet has been credited.')}"
                )
            except Exception as telegram_error:
                logger.error(f"Failed to send success message via Telegram: {telegram_error}")
            
            context.user_data.clear()
            return ConversationHandler.END
        else:
            # OTP submitted but payment pending - verify immediately
            try:
                await update.message.reply_text(
                    f"⏳ OTP submitted. Verifying payment status..."
                )
            except Exception as telegram_error:
                logger.error(f"Failed to send verification status message via Telegram: {telegram_error}")                
            await asyncio.sleep(2)
            
            # Try to verify the transaction immediately
            try:
                logger.info(f"Verifying transaction: {reference}")
                client = BackendAPIClient.get_client()
                verify_response = await client.post(
                    f"{settings.BACKEND_API_URL}/api/v1/wallet/deposit/verify/{reference}",
                    headers=headers,
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
                    
                    try:
                        await update.message.reply_text(
                            f"✅ Deposit verified and wallet credited!{wallet_info}\n\n"
                            f"Your wallet has been updated with the deposit amount."
                        )
                    except Exception as telegram_error:
                        logger.error(f"Failed to send verification success message via Telegram: {telegram_error}")
                elif verify_data.get("status") == "pending":
                    # Still pending - check again after a short delay
                    await asyncio.sleep(3)
                    
                    # Second verification attempt
                    try:
                        client = BackendAPIClient.get_client()
                        verify_response2 = await client.post(
                            f"{settings.BACKEND_API_URL}/api/v1/wallet/deposit/verify/{reference}",
                            headers=headers,
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
                            
                            try:
                                await update.message.reply_text(
                                    f"✅ Payment verified! Your wallet has been credited.{wallet_info}"
                                )
                            except Exception as telegram_error:
                                logger.error(f"Failed to send second verification success message via Telegram: {telegram_error}")
                        else:
                            try:
                                await update.message.reply_text(
                                    f"⏳ Payment is still being processed.\n\n"
                                    f"If your payment was successful, your wallet will be credited shortly.\n"
                                    f"You can check your balance using the 💼 Balance button."
                                )
                            except Exception as telegram_error:
                                logger.error(f"Failed to send pending status message via Telegram: {telegram_error}")
                    except Exception:
                        # Second verification failed, but that's okay
                        try:
                            await update.message.reply_text(
                                f"⏳ Payment is being processed.\n\n"
                                f"If your payment was successful, your wallet will be credited shortly.\n"
                                f"You can check your balance using the 💼 Balance button."
                            )
                        except Exception as telegram_error:
                            logger.error(f"Failed to send processing status message via Telegram: {telegram_error}")
                else:
                    try:
                        await update.message.reply_text(
                            f"⚠️ Payment status: {verify_data.get('paystack_status', 'unknown')}\n\n"
                            f"Please check your balance. If the payment was successful but balance wasn't updated, "
                            f"please contact support."
                        )
                    except Exception as telegram_error:
                        logger.error(f"Failed to send payment status message via Telegram: {telegram_error}")
            except Exception as verify_error:
                logger.error(f"Verification error: {verify_error}", exc_info=True)
                # Verification failed, but OTP was submitted
                try:
                    await update.message.reply_text(
                        f"⏳ OTP submitted successfully.\n\n"
                        f"Payment is being processed. If your payment was successful, "
                        f"your wallet will be credited automatically via webhook.\n\n"
                        f"You can check your balance using the 💼 Balance button."
                    )
                except Exception as telegram_error:
                    logger.error(f"Failed to send OTP submitted message via Telegram: {telegram_error}")
        
            context.user_data.clear()
            return ConversationHandler.END
            
    except httpx.HTTPStatusError as e:
        error_msg = "Unknown error"
        try:
            error_data = e.response.json()
            error_msg = error_data.get("detail", "Unknown error")
        except Exception as json_error:
            logger.warning(f"Failed to parse error response JSON: {json_error}")
            error_msg = str(e)
        
        logger.error(f"OTP verification failed with HTTP error: {error_msg}")
        
        try:
            await update.message.reply_text(
                f"❌ OTP verification failed\n\n"
                f"Error: {error_msg}\n\n"
                "Please try the deposit again."
            )
        except Exception as telegram_error:
            logger.error(f"Failed to send OTP error message via Telegram: {telegram_error}")
        
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Unexpected error in deposit_otp: {e}", exc_info=True)
        
        try:
            await update.message.reply_text(
                f"❌ An error occurred: {str(e)}\n\n"
                "Please try again later."
            )
        except Exception as telegram_error:
            logger.error(f"Failed to send error message via Telegram: {telegram_error}")
        
        context.user_data.clear()
        return ConversationHandler.END


async def deposit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel deposit flow or handle keyboard button."""
    # Clear conversation data
    context.user_data.clear()
    
    message_text = update.message.text.strip() if update.message else ""
    keyboard_buttons = ["💼 Balance", "➕ Deposit", "🌐 Bundles", "📜 History", "🎯 Referral", "❓ Help"]
    
    if message_text not in keyboard_buttons:
        # Regular cancel
        await update.message.reply_text(
            "❌ Deposit cancelled."
        )
    
    return ConversationHandler.END