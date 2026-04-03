import httpx
import logging
from app.core.config import settings
from app.utils.phone_utils import normalize_phone_number
from app.services.whatsapp_notifier import WhatsAppNotifierService
from app.utils.backend_client import BackendAPIClient


logger = logging.getLogger(__name__)


async def history_handler(phone_number: str, bot) -> None:
    """
    Handle history request.
    
    Args:
        phone_number: User's phone number
        bot: WhatsAppBot instance
    """
    try:
        normalized_phone = normalize_phone_number(phone_number)
        notifier = WhatsAppNotifierService()
        
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
        
        # Get authentication headers
        headers = BackendAPIClient.get_auth_headers(normalized_phone, "whatsapp")
        
        # Get history from backend API with retry logic
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            try:
                client = BackendAPIClient.get_client()
                response = await client.get(
                    f"{settings.BACKEND_API_URL}/api/v1/users/{normalized_phone}/history",
                    params={"limit": 10, "identifier_type": "phone"},
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                break  # Success, exit retry loop
            except (httpx.RemoteProtocolError, httpx.ConnectError) as conn_error:
                if attempt < max_retries:
                    logger.warning(f"Connection error (attempt {attempt + 1}/{max_retries + 1}), resetting client: {conn_error}")
                    await BackendAPIClient.reset_client()
                else:
                    raise
        
        transactions = data.get("transactions", [])
        orders = data.get("orders", [])
        
        # Format transactions
        history_text = "📜 TRANSACTION HISTORY\n\n"

        if transactions:
            history_text += "💳 Transactions:\n"
            for t in transactions[:5]:  # Show last 5
                status_emoji = "✅" if t['status'] == "success" else "❌" if t['status'] == "failed" else "⏳"
                history_text += (
                    f"{status_emoji} {t['type'].upper()}: {t['currency']} {t['amount']} "
                    f"({t['status']})\n"
                    f"Ref: {t['reference'][:20]}...\n\n"
                )
        else:
            history_text += "No transactions yet.\n\n"
        
        history_text += "📦 Orders:\n"
        if orders:
            for o in orders[:5]:  # Show last 5
                status_emoji = "✅" if o['status'] == "success" else "❌" if o['status'] == "failed" else "⏳"
                history_text += (
                    f"{status_emoji} GHS {o['price']} "
                    f"({o['status']})\n"
                )
                if o.get('vendor_reference'):
                    history_text += f"Ref: {o['vendor_reference'][:20]}...\n"
                history_text += "\n"
        else:
            history_text += "No orders yet.\n"
        
        await bot.send_main_menu(normalized_phone, history_text)
                
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to get history: {e}")
        await bot.send_main_menu(
            normalized_phone,
            f"⚠️ Error fetching history: {e.response.status_code}\n\nPlease try again later."
        )
    except Exception as e:
        logger.error(f"Error in history handler: {str(e)}", exc_info=True)
        await notifier.send_text_message(
            normalized_phone,
            "❌ An error occurred. Please try again later."
        )
