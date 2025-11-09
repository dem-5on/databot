import uuid
from decimal import Decimal
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request
from app.repository.user_repo import UserRepository
from app.repository.transaction_repo import TransactionRepository
from app.services.notifier import NotifierService
from app.services.wallet_service import WalletService
from app.services.paystack_service import PaystackService
from app.core.constants import TransactionType, TransactionStatus

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
async def init_deposit(request: DepositInitRequest):
    """
    Initialize a deposit transaction and create Paystack charge.
    """
    user_repo = UserRepository()
    transaction_repo = TransactionRepository()
    
    # Get or create user
    user, _ = user_repo.get_or_create(request.telegram_id)
    
    # Generate unique reference
    reference = f"DEP-{uuid.uuid4()}"
    
    # Create transaction record
    transaction = transaction_repo.create_transaction(
        user_id=user["id"],
        transaction_type=TransactionType.DEPOSIT.value,
        amount=request.amount,
        currency="GHS",
        reference=reference,
        status=TransactionStatus.PENDING.value,
        phone=request.phone,
        provider=request.provider
    )
    
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
        transaction_repo.update_transaction_status(
            transaction["id"],
            TransactionStatus.PENDING.value,
            raw_payload=paystack_response
        )
        
        return {
            "status": "success",
            "reference": reference,
            "paystack_response": paystack_response,
            "display_text": paystack_response.get("data", {}).get("display_text", "You'll receive a MoMo prompt; approve it to complete.")
        }
    except Exception as e:
        transaction_repo.update_transaction_status(
            transaction["id"],
            TransactionStatus.FAILED.value,
            raw_payload={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=f"Failed to initiate charge: {str(e)}")


@router.get("/balance/{telegram_id}")
async def get_balance(telegram_id: str):
    """Get wallet balance for user."""
    user_repo = UserRepository()
    wallet_service = WalletService()
    
    user = user_repo.get_by_telegram_id(telegram_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    balance = await wallet_service.get_balance(user["id"])
    
    return {
        "telegram_id": telegram_id,
        "balance": str(balance),
        "currency": "GHS"
    }


@router.post("/deposit/confirm")
async def confirm_deposit(request: DepositConfirmRequest):
    """
    Submit OTP to confirm mobile money deposit.
    """
    transaction_repo = TransactionRepository()
    wallet_service = WalletService()
    
    # Get transaction
    transaction = transaction_repo.get_by_reference(request.reference)
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if transaction["status"] == TransactionStatus.SUCCESS.value:
        raise HTTPException(status_code=400, detail="Transaction already completed")
    
    if transaction["status"] == TransactionStatus.FAILED.value:
        raise HTTPException(status_code=400, detail="Transaction already failed")
    
    # Submit OTP to Paystack
    paystack_service = PaystackService()
    try:
        # Get the Paystack reference from stored payload
        raw_payload = transaction.get("raw_payload") or {}
        paystack_ref = raw_payload.get("data", {}).get("reference")
        
        if not paystack_ref:
            raise ValueError("No Paystack reference found in transaction")
        
        # Submit OTP
        submit_response = await paystack_service.submit_otp(
            reference=paystack_ref,
            otp=request.otp
        )
        
        # Update transaction with OTP submission response
        updated_payload = raw_payload.copy()
        updated_payload["otp_submission"] = submit_response
        transaction_repo.update_transaction_status(
            transaction["id"],
            transaction["status"],
            raw_payload=updated_payload
        )
        
        # Check if payment was successful
        response_status = submit_response.get("data", {}).get("status")
        
        if response_status == "success":
            # Payment successful - credit wallet (idempotent operation)
            # credit_wallet will check transaction status and prevent double crediting
            try:
                await wallet_service.credit_wallet(
                    user_id=transaction["user_id"],
                    amount=Decimal(transaction["amount"]),
                    reference=transaction["reference"]
                )
                
                return {
                    "status": "success",
                    "message": f"Deposit of GHS {transaction['amount']} successful! Your wallet has been credited."
                }
            except ValueError as e:
                # Transaction already processed (idempotency check)
                error_str = str(e).lower()
                if "already processed" in error_str or "already credited" in error_str:
                    return {
                        "status": "success",
                        "message": f"Deposit of GHS {transaction['amount']} successful! Your wallet has been credited."
                    }
                else:
                    raise
        else:
            # Payment not yet confirmed or failed
            return {
                "status": "pending",
                "message": "Payment is being processed. Please wait a moment.",
                "paystack_status": response_status
            }
            
    except Exception as e:
        transaction_repo.update_transaction_status(
            transaction["id"],
            TransactionStatus.FAILED.value,
            raw_payload={"otp_error": str(e)}
        )
        raise HTTPException(status_code=400, detail=f"Failed to confirm deposit: {str(e)}")


@router.post("/deposit/verify/{reference}")
async def verify_deposit(reference: str):
    """
    Manually verify a deposit transaction by checking Paystack status.
    This is useful if the webhook didn't fire or was missed.
    """
    transaction_repo = TransactionRepository()
    wallet_service = WalletService()
    paystack_service = PaystackService()
    
    # Get transaction
    transaction = transaction_repo.get_by_reference(reference)
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Check if already processed
    if transaction["status"] == TransactionStatus.SUCCESS.value:
        return {
            "status": "success",
            "message": "Transaction already completed",
            "transaction": transaction
        }
    
    # Get Paystack reference
    raw_payload = transaction.get("raw_payload") or {}
    paystack_ref = raw_payload.get("data", {}).get("reference")
    
    if not paystack_ref:
        raise HTTPException(status_code=400, detail="No Paystack reference found in transaction")
    
    try:
        # Verify transaction with Paystack
        verify_response = await paystack_service.verify_transaction(paystack_ref)
        
        # Update transaction with verification response
        updated_payload = raw_payload.copy()
        updated_payload["verification"] = verify_response
        transaction_repo.update_transaction_status(
            transaction["id"],
            transaction["status"],
            raw_payload=updated_payload
        )
        
        # Check transaction status
        transaction_data = verify_response.get("data", {})
        paystack_status = transaction_data.get("status")
        
        if paystack_status == "success":
            
            try:
                # This will only credit if transaction is not already SUCCESS
                wallet = await wallet_service.credit_wallet(
                    user_id=transaction["user_id"],
                    amount=Decimal(transaction["amount"]),
                    reference=transaction["reference"]
                )
                
                # Re-fetch transaction to check if it was actually credited
                # (it might have been credited by webhook in the meantime)
                updated_transaction = transaction_repo.get_by_reference(reference)
                was_just_credited = (
                    updated_transaction and 
                    updated_transaction["status"] == TransactionStatus.SUCCESS.value and
                    updated_transaction.get("raw_payload", {}).get("wallet_credited")
                )
                
                # Only award referral bonus and notify if we just credited
                # (to avoid duplicate notifications if webhook already processed it)
                if was_just_credited:
                    # Award referral bonus
                    from app.services.referral_service import ReferralService
                    referral_service = ReferralService()
                    await referral_service.award_referral_bonus(transaction["user_id"])
                    
                    # Notify user (only if we just credited, not if webhook already did)
                    user_repo = UserRepository()
                    user = user_repo.get_by_id(transaction["user_id"])
                    if user:
                        await NotifierService.send_user_message(
                            telegram_id=int(user["telegram_id"]),
                            text=f"✅ <b>Deposit Successful!</b>\n\n"
                                 f"Amount: GHS {transaction['amount']}\n"
                                 f"Your wallet has been credited.\n"
                                 f"New balance available {wallet['balance']} for purchases."
                        )
                else:
                    # Wallet was already credited by another process (likely webhook)
                    import logging
                    logging.info(f"Transaction {reference} was already credited by another process")
            
            except ValueError as e:
                # Transaction already processed (idempotency check)
                if "already processed" in str(e).lower() or "already credited" in str(e).lower():
                    return {
                        "status": "success",
                        "message": "Transaction already processed and wallet credited",
                        "paystack_status": paystack_status,
                        "transaction": transaction_repo.get_by_reference(reference)
                    }
                else:
                    raise
            
            return {
                "status": "success",
                "message": "Transaction verified and wallet credited",
                "paystack_status": paystack_status,
                "transaction": transaction_repo.get_by_reference(reference)
            }
        elif paystack_status == "failed":
            # Payment failed
            transaction_repo.update_transaction_status(
                transaction["id"],
                TransactionStatus.FAILED.value,
                raw_payload=updated_payload
            )
            return {
                "status": "failed",
                "message": "Transaction failed",
                "paystack_status": paystack_status
            }
        else:
            # Still pending
            return {
                "status": "pending",
                "message": "Transaction is still pending",
                "paystack_status": paystack_status
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to verify transaction: {str(e)}")
