import httpx
from telegram import Update
from telegram.ext import ContextTypes
from app.core.config import settings


async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle history request."""
    user = update.effective_user
    telegram_id = str(user.id)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.BACKEND_API_URL}/api/v1/users/{telegram_id}/history",
                params={"limit": 10},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            
            transactions = data.get("transactions", [])
            orders = data.get("orders", [])
            
            # Format transactions
            trans_text = "📜 Transaction History\n\n"
            
            if transactions:
                trans_text += "💳 Transactions:\n"
                for t in transactions[:5]:  # Show last 5
                    status_emoji = "✅" if t['status'] == "success" else "❌" if t['status'] == "failed" else "⏳"
                    trans_text += (
                        f"{status_emoji} {t['type'].upper()}: {t['currency']} {t['amount']} "
                        f"({t['status']})\n"
                        f"  Ref: {t['reference'][:20]}...\n\n"
                    )
            else:
                trans_text += "No transactions yet.\n\n"
            
            trans_text += "📦 Orders:\n"
            if orders:
                for o in orders[:5]:  # Show last 5
                    status_emoji = "✅" if o['status'] == "success" else "❌" if o['status'] == "failed" else "⏳"
                    trans_text += (
                        f"{status_emoji} GHS {o['price']} "
                        f"({o['status']})\n"
                    )
                    if o.get('vendor_reference'):
                        trans_text += f"  Ref: {o['vendor_reference'][:20]}...\n"
                    trans_text += "\n"
            else:
                trans_text += "No orders yet.\n"
            
            await update.message.reply_text(trans_text)
            
    except httpx.HTTPStatusError as e:
        await update.message.reply_text(
            f"⚠️ Error fetching history: {e.response.status_code}\n"
            f"Please try again later."
        )
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ An error occurred: {str(e)}\n"
            "Please try again later."
        )

