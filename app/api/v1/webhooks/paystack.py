import json
from sqlalchemy import select
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.notifier import NotifierService
from app.services.wallet_service import WalletService
from app.services.paystack_service import PaystackService
from app.models.transaction import Transaction, TransactionStatus
from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks

router = APIRouter()


@router.post("")
async def paystack_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
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
    
    # Parse webhook payload
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    event = payload.get("event")
    data = payload.get("data", {})
    reference = data.get("reference")
    
    if not reference:
        raise HTTPException(status_code=400, detail="Missing reference in webhook payload")
    
    # Find transaction by reference
    stmt = select(Transaction).where(Transaction.reference == reference)
    result = await db.execute(stmt)
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Handle idempotency - if already processed, ignore
    if transaction.status == TransactionStatus.SUCCESS:
        return {"status": "ok", "message": "Already processed"}
    
    # Store webhook payload
    transaction.raw_payload = payload
    
    # Process event
    if event == "charge.success":
        # Credit wallet
        try:
            wallet = await WalletService.credit_wallet(
                db=db,
                user_id=transaction.user_id,
                amount=transaction.amount,
                reference=reference
            )
            
            # Send admin notification in background
            background_tasks.add_task(
                NotifierService.send_admin_alert,
                f"✅ Deposit Success\n"
                f"User: {transaction.user_id}\n"
                f"Amount: GHS {transaction.amount}\n"
                f"Reference: {reference}"
            )
            
            return {"status": "ok", "message": "Wallet credited"}
        except Exception as e:
            transaction.status = TransactionStatus.FAILED
            transaction.raw_payload = {**payload, "error": str(e)}
            await db.commit()
            raise HTTPException(status_code=500, detail=f"Failed to credit wallet: {str(e)}")
    
    elif event == "charge.failed":
        # Mark transaction as failed
        transaction.status = TransactionStatus.FAILED
        await db.commit()
        
        return {"status": "ok", "message": "Transaction marked as failed"}
    
    else:
        # Unknown event, just acknowledge
        return {"status": "ok", "message": f"Event {event} received but not processed"}

