import httpx
from telegram import Update
from app.core.config import settings
from telegram.ext import ContextTypes
from app.utils.backend_client import BackendAPIClient


async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /referral command to show user's referral code and stats."""
    user = update.effective_user
    telegram_id = str(user.id)
    
    try:
        # Get authentication headers
        headers = BackendAPIClient.get_auth_headers(telegram_id, "telegram")
        
        # Retry logic for connection errors
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                client = BackendAPIClient.get_client()
                
                # Get referral code
                code_response = await client.get(
                    f"{settings.BACKEND_API_URL}/api/v1/referrals/code/{telegram_id}",
                    headers=headers,
                )
                code_response.raise_for_status()
                code_data = code_response.json()
                
                # Get referral stats
                stats_response = await client.get(
                    f"{settings.BACKEND_API_URL}/api/v1/referrals/referrals/{telegram_id}",
                    headers=headers,
                )
                stats_response.raise_for_status()
                stats_data = stats_response.json()
                break  # Success
            except (httpx.RemoteProtocolError, httpx.ConnectError) as conn_error:
                if attempt < max_retries:
                    await BackendAPIClient.reset_client()
                else:
                    raise
        
        referral_code = code_data.get("referral_code", "N/A")
        total_referrals = stats_data.get("total_referrals", 0)
        referrals = stats_data.get("referrals", [])
        bonuses_paid = sum(1 for r in referrals if r.get("bonus_paid"))
        
        # Get bot username for referral link
        bot_username = context.bot.username if context.bot and hasattr(context.bot, 'username') else "your_bot"
        referral_link = f"https://t.me/{bot_username}?start={referral_code}"
        
        message = (
            f"🎯 <b>Your Referral Program</b>\n\n"
            f"📝 <b>Your Referral Code:</b> <code>{referral_code}</code>\n\n"
            f"🔗 <b>Your Referral Link:</b>\n{referral_link}\n\n"
            f"📊 <b>Statistics:</b>\n"
            f"• Total Referrals: {total_referrals}\n"
            f"• Bonuses Paid: {bonuses_paid}\n"
            f"• Pending: {total_referrals - bonuses_paid}\n\n"
            f"💰 <b>How it works:</b>\n"
            f"• Share your referral link with friends\n"
            f"• When they complete their first transaction (deposit or purchase),\n"
            f"  you'll receive GHS {settings.REFERRAL_BONUS_AMOUNT} bonus!\n"
            f"• The bonus is automatically added to your wallet balance.\n\n"
            f"💡 <b>Tip:</b> Share your referral link to earn more rewards!"
        )
        
        await update.message.reply_text(message, parse_mode="HTML")
            
    except httpx.HTTPStatusError as e:
        await update.message.reply_text(
            f"⚠️ Error fetching referral information: {e.response.status_code}\n"
            f"Please try again later."
        )
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ An error occurred. Please try again later."
        )
