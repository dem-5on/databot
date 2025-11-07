from telegram import Update
from telegram.ext import ContextTypes
import httpx
from app.core.config import settings


async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle balance check."""
    user = update.effective_user
    telegram_id = str(user.id)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.BACKEND_API_URL}/api/v1/wallet/balance/{telegram_id}",
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            
            balance = data.get("balance", "0.00")
            currency = data.get("currency", "GHS")
            
            await update.message.reply_text(
                f"💼 Your Wallet Balance\n\n"
                f"Amount: {currency} {balance}\n\n"
                "Use ➕ Deposit to add funds to your wallet."
            )
    except httpx.HTTPStatusError as e:
        await update.message.reply_text(
            f"⚠️ Error fetching balance: {e.response.status_code}\n"
            f"Please try again later."
        )
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ An error occurred: {str(e)}\n"
            "Please try again later."
        )

