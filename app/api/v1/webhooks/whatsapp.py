import logging
import hmac
import hashlib
from fastapi import APIRouter, Request, HTTPException, Query
from app.core.config import settings
from whatsapp.whatsapp_bot import WhatsAppBot

logger = logging.getLogger(__name__)

router = APIRouter()

bot = WhatsAppBot()

@router.get("")
async def verify_webhook(
    mode: str = Query(..., alias="hub.mode"),
    token: str = Query(..., alias="hub.verify_token"),
    challenge: str = Query(..., alias="hub.challenge")
):
    """
    Verify WhatsApp webhook.
    
    WhatsApp will send a GET request to verify the webhook URL.
    This endpoint must return the challenge if the token matches.
    """
    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully")
        return int(challenge)
    else:
        logger.warning(f"WhatsApp webhook verification failed: mode={mode}, token={token}")
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("")
async def handle_webhook(request: Request):
    """
    Handle incoming WhatsApp webhook events.
    
    This endpoint receives messages and status updates from WhatsApp.
    """
    try:
        # Get request body
        body = await request.body()
        
        # Verify webhook signature if secret is configured (optional but recommended)
        if settings.WHATSAPP_APP_SECRET:
            signature = request.headers.get("X-Hub-Signature-256", "")
            if not _verify_signature(body, signature, settings.WHATSAPP_APP_SECRET):
                logger.warning("Invalid webhook signature")
                raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Parse JSON payload
        import json
        payload = json.loads(body.decode('utf-8'))
        
        # WhatsApp sends events in 'entry' array
        if "object" in payload and payload["object"] == "whatsapp_business_account":
            for entry in payload.get("entry", []):
                # Each entry can have changes
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    
                    # Handle messages
                    if "messages" in value:
                        event = {
                            "messages": value["messages"],
                            "statuses": value.get("statuses", [])
                        }
                        await bot.handle_webhook_event(event)
                    
                    # Handle status updates only
                    elif "statuses" in value:
                        event = {
                            "messages": [],
                            "statuses": value["statuses"]
                        }
                        await bot.handle_webhook_event(event)
        
        # Return 200 immediately to acknowledge receipt
        return {"status": "ok"}
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook payload: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}", exc_info=True)
        # Still return 200 to prevent WhatsApp from retrying
        return {"status": "error", "message": str(e)}


def _verify_signature(body: bytes, signature: str, secret: str) -> bool:
    """
    Verify webhook signature using HMAC SHA256.
    
    Args:
        body: Request body as bytes
        signature: Signature from X-Hub-Signature-256 header (format: "sha256=...")
        secret: Webhook secret
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature:
        return False
    
    # Extract hash from signature (format: "sha256=HASH")
    if signature.startswith("sha256="):
        signature_hash = signature[7:]
    else:
        return False
    
    # Compute HMAC SHA256
    computed_hash = hmac.new(
        secret.encode('utf-8'),
        body,
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison
    return hmac.compare_digest(computed_hash, signature_hash)

