"""Paystack webhook handler using Supabase repositories."""
import json
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from app.repository.transaction_repo import TransactionRepository
from app.repository.user_repo import UserRepository
from app.services.notifier import NotifierService
from app.services.wallet_service import WalletService
from app.services.paystack_service import PaystackService
from app.services.referral_service import ReferralService
from app.core.constants import TransactionStatus
from decimal import Decimal

router = APIRouter()


@router.post("")
async def paystack_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Handle Paystack webhook events.
    Verifies signature and processes charge.success/charge.failed events.
    """
    # Get raw body for signature verification
    body = await request.body()
    
    # Get signature from header
    signature_header = request.headers.get("X-Paystack-Signature", "")
    
    # Verify signature
    paystack_service = PaystackService()
    if not paystack_service.verify_webhook_signature(body, signature_header):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse webhook payload from body (since we already read it)
    try:
        payload = json.loads(body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {str(e)}")
    
    event = payload.get("event")
    data = payload.get("data", {})
    paystack_ref = data.get("reference")
    
    if not paystack_ref:
        raise HTTPException(status_code=400, detail="Missing reference in webhook payload")
    
    transaction_repo = TransactionRepository()
    
    # Find transaction by Paystack reference
    transaction = transaction_repo.get_by_paystack_reference(paystack_ref)
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Handle idempotency - if already processed, ignore
    if transaction["status"] == TransactionStatus.SUCCESS.value:
        # Double-check payload to ensure wallet was credited
        raw_payload = transaction.get("raw_payload") or {}
        if isinstance(raw_payload, dict) and raw_payload.get("wallet_credited"):
            return {"status": "ok", "message": "Already processed and wallet credited"}
        # If status is SUCCESS but no wallet_credited flag, log warning
        import logging
        logging.warning(f"Transaction {transaction['reference']} has SUCCESS status but no wallet_credited flag")
        return {"status": "ok", "message": "Already processed"}
    
    # Store webhook payload
    updated_payload = transaction.get("raw_payload") or {}
    if isinstance(updated_payload, dict):
        updated_payload["webhook_data"] = payload
    else:
        updated_payload = {"webhook_data": payload}
    
    transaction_repo.update_transaction_status(
        transaction["id"],
        transaction["status"],
        raw_payload=updated_payload
    )
    
    # Process event
    if event == "charge.success":
        # Credit wallet (idempotent - will check status internally)
        try:
            wallet_service = WalletService()
            # Convert amount string to Decimal
            amount = Decimal(str(transaction["amount"]))
            
            # credit_wallet is now idempotent - it checks transaction status before crediting
            await wallet_service.credit_wallet(
                user_id=transaction["user_id"],
                amount=amount,
                reference=transaction["reference"]
            )
            
            # Send admin notification in background
            background_tasks.add_task(
                NotifierService.send_admin_alert,
                f"✅ Deposit Success\n"
                f"User: {transaction['user_id']}\n"
                f"Amount: GHS {transaction['amount']}\n"
                f"Reference: {transaction['reference']}"
            )
            
            # Award referral bonus if this is user's first successful transaction
            referral_service = ReferralService()
            await referral_service.award_referral_bonus(transaction["user_id"])
            
            # Notify user
            user_repo = UserRepository()
            user = user_repo.get_by_id(transaction["user_id"])
            if user:
                await NotifierService.send_user_message(
                    telegram_id=int(user["telegram_id"]),
                    text=f"✅ <b>Deposit Successful!</b>\n\n"
                         f"Amount: GHS {transaction['amount']}\n"
                         f"Your wallet has been credited.\n"
                         f"New balance available for purchases."
                )
            
            return {"status": "ok", "message": "Wallet credited"}
        except Exception as e:
            transaction_repo.update_transaction_status(
                transaction["id"],
                TransactionStatus.FAILED.value,
                raw_payload={**updated_payload, "error": str(e)}
            )
            raise HTTPException(status_code=500, detail=f"Failed to credit wallet: {str(e)}")
    
    elif event == "charge.failed":
        # Mark transaction as failed
        transaction_repo.update_transaction_status(
            transaction["id"],
            TransactionStatus.FAILED.value,
            raw_payload=updated_payload
        )
        
        return {"status": "ok", "message": "Transaction marked as failed"}
    
    else:
        # Unknown event, just acknowledge
        return {"status": "ok", "message": f"Event {event} received but not processed"}
