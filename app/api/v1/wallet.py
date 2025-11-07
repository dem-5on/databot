import uuid
from decimal import Decimal
from sqlalchemy import select
from app.models.user import User
from app.db.session import get_db
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.notifier import NotifierService
from app.services.wallet_service import WalletService
from app.services.paystack_service import PaystackService
from fastapi import APIRouter, Depends, HTTPException, Request
from app.models.transaction import Transaction, TransactionType, TransactionStatus

router = APIRouter()


class DepositInitRequest(BaseModel):
    telegram_id: str
    amount: Decimal
    phone: str
    provider: str  # MTN, VODAFONE, AIRTELTIGO



class DepositConfirmRequest(BaseModel):
    reference: str  # The DEP-xxx reference
    otp: str


@router.post("/deposit/init")
async def init_deposit(
    request: DepositInitRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Initialize a deposit transaction and create Paystack charge.
    """
    # Get or create user
    stmt = select(User).where(User.telegram_id == request.telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate unique reference
    reference = f"DEP-{uuid.uuid4()}"
    
    # Create transaction record
    transaction = Transaction(
        user_id=user.id,
        type=TransactionType.DEPOSIT,
        amount=request.amount,
        currency="GHS",
        reference=reference,
        status=TransactionStatus.PENDING,
        phone=request.phone,
        provider=request.provider
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)
    
    # Create Paystack charge
    paystack_service = PaystackService()
    try:
        # Use a dummy email if user doesn't have one
        email = f"user_{request.telegram_id}@databot.com"
        
        paystack_response = await paystack_service.create_mobile_money_charge(
            email=email,
            amount_ghs=request.amount,
            phone=request.phone,
            provider=request.provider
        )
        
        # Store Paystack response in transaction
        transaction.raw_payload = paystack_response
        await db.commit()
        
        return {
            "status": "success",
            "reference": reference,
            "paystack_response": paystack_response,
            "display_text": paystack_response.get("data", {}).get("display_text", "You'll receive a MoMo prompt; approve it to complete.")
        }
    except Exception as e:
        transaction.status = TransactionStatus.FAILED
        transaction.raw_payload = {"error": str(e)}
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to initiate charge: {str(e)}")


@router.get("/balance/{telegram_id}")
async def get_balance(
    telegram_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get wallet balance for user."""
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    balance = await WalletService.get_balance(db, user.id)
    
    return {
        "telegram_id": telegram_id,
        "balance": str(balance),
        "currency": "GHS"
    }


@router.post("/deposit/confirm")
async def confirm_deposit(
    request: DepositConfirmRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit OTP to confirm mobile money deposit.
    """
    # Get transaction
    stmt = select(Transaction).where(Transaction.reference == request.reference)
    result = await db.execute(stmt)
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if transaction.status == TransactionStatus.SUCCESS:
        raise HTTPException(status_code=400, detail="Transaction already completed")
    
    if transaction.status == TransactionStatus.FAILED:
        raise HTTPException(status_code=400, detail="Transaction already failed")
    
    # Submit OTP to Paystack
    paystack_service = PaystackService()
    try:
        # Get the Paystack reference from stored payload
        paystack_ref = transaction.raw_payload.get("data", {}).get("reference")
        
        if not paystack_ref:
            raise ValueError("No Paystack reference found in transaction")
        
        # Submit OTP
        submit_response = await paystack_service.submit_otp(
            reference=paystack_ref,
            otp=request.otp
        )
        
        # Update transaction with OTP submission response
        if not transaction.raw_payload:
            transaction.raw_payload = {}
        transaction.raw_payload["otp_submission"] = submit_response
        
        # Check if payment was successful
        response_status = submit_response.get("data", {}).get("status")
        
        if response_status == "success":
            # Payment successful - update transaction and credit wallet
            transaction.status = TransactionStatus.SUCCESS
            await db.commit()
            
            # Credit wallet
            await WalletService.credit_wallet(
                db=db,
                user_id=transaction.user_id,
                amount=transaction.amount,
                reference=transaction.reference
            )
            
            return {
                "status": "success",
                "message": f"Deposit of GHS {transaction.amount} successful! Your wallet has been credited."
            }
        else:
            # Payment not yet confirmed or failed
            await db.commit()
            return {
                "status": "pending",
                "message": "Payment is being processed. Please wait a moment.",
                "paystack_status": response_status
            }
            
    except Exception as e:
        transaction.status = TransactionStatus.FAILED
        if not transaction.raw_payload:
            transaction.raw_payload = {}
        transaction.raw_payload["otp_error"] = str(e)
        await db.commit()
        raise HTTPException(status_code=400, detail=f"Failed to confirm deposit: {str(e)}")
    



@router.post("/paystack/webhook")
async def paystack_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Paystack webhook notifications for payment status updates.
    """
    # Get raw body for signature verification
    body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")
    
    # Verify webhook signature
    paystack_service = PaystackService()
    if not paystack_service.verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse webhook data
    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    event = data.get("event")
    event_data = data.get("data", {})
    
    # Handle charge.success event
    if event == "charge.success":
        # Get Paystack reference
        paystack_ref = event_data.get("reference")
        
        if not paystack_ref:
            return {"status": "ignored", "reason": "no reference"}
        
        # Find transaction by Paystack reference in raw_payload
        stmt = select(Transaction).where(
            Transaction.raw_payload.op("->")("data").op("->>")("reference") == paystack_ref
        )
        result = await db.execute(stmt)
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            return {"status": "ignored", "reason": "transaction not found"}
        
        if transaction.status == TransactionStatus.SUCCESS:
            return {"status": "ignored", "reason": "already processed"}
        
        # Update transaction status
        transaction.status = TransactionStatus.SUCCESS
        transaction.raw_payload["webhook_data"] = event_data
        await db.commit()
        
        # Credit wallet
        await WalletService.credit_wallet(
            db=db,
            user_id=transaction.user_id,
            amount=transaction.amount,
            reference=transaction.reference
        )
        
        # Award referral bonus if this is user's first successful transaction
        from app.services.referral_service import ReferralService
        await ReferralService.award_referral_bonus(db, transaction.user_id)
        
        # Notify user
        from app.models.user import User
        user_stmt = select(User).where(User.id == transaction.user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if user:
            await NotifierService.send_user_message(
                telegram_id=int(user.telegram_id),
                text=f"✅ <b>Deposit Successful!</b>\n\n"
                     f"Amount: GHS {transaction.amount}\n"
                     f"Your wallet has been credited.\n"
                     f"New balance available for purchases."
            )
        
        return {"status": "success"}
    
    return {"status": "ignored", "event": event}