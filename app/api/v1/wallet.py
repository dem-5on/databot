import uuid
import logging
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request
from app.services.notifier import NotifierService
from app.services.wallet_service import WalletService
from app.services.paystack_service import PaystackService
from app.services.referral_service import ReferralService
from app.core.constants import TransactionType, TransactionStatus
from app.repository.transaction_repo import TransactionRepository
from app.core.rate_limit import limiter


router = APIRouter()

class DepositInitRequest(BaseModel):
    telegram_id: Optional[str] = None  # Optional, for Telegram users
    user_id: Optional[str] = None  # Optional, for WhatsApp users (can pass user_id directly)
    amount: Decimal
    phone: str
    provider: str  # MTN, VODAFONE, AIRTELTIGO


class DepositConfirmRequest(BaseModel):
    reference: str  # The DEP-xxx reference
    otp: str


@router.post("/deposit/init")
@limiter.limit("5/minute")
async def init_deposit(request: Request, deposit_data: DepositInitRequest):
    """
    Initialize a deposit transaction and create Paystack charge.
    """
    from app.services.user_service import UserService
    
    user_service = UserService()
    transaction_repo = TransactionRepository()
    
    # Get user - either by user_id (WhatsApp) or telegram_id (Telegram)
    if deposit_data.user_id:
        # WhatsApp: user_id provided directly
        from app.repository.base_user_repo import BaseUserRepository
        base_user_repo = BaseUserRepository()
        user = await base_user_repo.get_by_id(deposit_data.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    elif deposit_data.telegram_id:
        # Telegram: use UserService for proper multi-table lookup
        user, _ = await user_service.get_or_create_telegram_user(deposit_data.telegram_id)
    else:
        raise HTTPException(status_code=400, detail="Either telegram_id or user_id must be provided")
    
    # Generate unique reference
    reference = f"DEP-{uuid.uuid4()}"
    
    # Create transaction record
    transaction = await transaction_repo.create_transaction(
        user_id=user["id"],
        transaction_type=TransactionType.DEPOSIT.value,
        amount=deposit_data.amount,
        currency="GHS",
        reference=reference,
        status=TransactionStatus.PENDING.value,
        phone=deposit_data.phone,
        provider=deposit_data.provider
    )
    
    # Create Paystack charge
    paystack_service = PaystackService()
    try:
        # Use this email if user doesn't have one
        user_identifier = deposit_data.telegram_id or deposit_data.user_id or user["id"]
        email = f"user_{user_identifier}@integers.com"
        
        paystack_response = await paystack_service.create_mobile_money_charge(
            email=email,
            amount_ghs=deposit_data.amount,
            phone=deposit_data.phone,
            provider=deposit_data.provider
        )
        
        # Store Paystack response in transaction
        await transaction_repo.update_transaction_status(
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
        await transaction_repo.update_transaction_status(
            transaction["id"],
            TransactionStatus.FAILED.value,
            raw_payload={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=f"Failed to initiate charge: {str(e)}")


@router.get("/balance/{identifier}")
async def get_balance(
    identifier: str,
    identifier_type: str = "telegram_id"  # "telegram_id" or "phone"
):
    """
    Get wallet balance for user.
    Can use either telegram_id or phone number as identifier.
    """
    from app.services.user_service import UserService
    
    user_service = UserService()
    wallet_service = WalletService()
    
    # Get user by identifier type
    if identifier_type == "phone":
        user = await user_service.get_user_by_whatsapp_phone(identifier)
    else:
        user = await user_service.get_user_by_telegram_id(identifier)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    balance = await wallet_service.get_balance(user["id"])
    
    return {
        "user_id": user["id"],
        "telegram_id": user.get("telegram_id"),
        "phone": user.get("whatsapp_phone"),
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
    transaction = await transaction_repo.get_by_reference(request.reference)
    
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
        await transaction_repo.update_transaction_status(
            transaction["id"],
            transaction["status"],
            raw_payload=updated_payload
        )
        
        # Check if payment was successful
        response_status = submit_response.get("data", {}).get("status")
        
        if response_status == "success":
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
        await transaction_repo.update_transaction_status(
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
    transaction = await transaction_repo.get_by_reference(reference)
    
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
        await transaction_repo.update_transaction_status(
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
                updated_transaction = await transaction_repo.get_by_reference(reference)
                was_just_credited = (
                    updated_transaction and 
                    updated_transaction["status"] == TransactionStatus.SUCCESS.value and
                    updated_transaction.get("raw_payload", {}).get("wallet_credited")
                )
                
                # Only award referral bonus and notify if we just credited
                if was_just_credited:
                    # Award referral bonus
                    referral_service = ReferralService()
                    await referral_service.award_referral_bonus(transaction["user_id"])
                    
                    # Notify user (only if we just credited, not if webhook already did)
                    from app.repository.base_user_repo import BaseUserRepository
                    user_repo = BaseUserRepository()
                    user = await user_repo.get_by_id(transaction["user_id"])
                    if user:
                        # Notify via Telegram if user has telegram_id
                        if user.get("telegram_id"):
                            await NotifierService.send_user_message(
                                telegram_id=int(user["telegram_id"]),
                                text=f"✅ <b>Deposit Successful!</b>\n\n"
                                     f"Amount: GHS {transaction['amount']}\n"
                                     f"Your wallet has been credited.\n"
                                     f"New balance available {wallet['balance']} for purchases."
                            )
                        # Notify via WhatsApp if user has phone number
                        if user.get("phone"):
                            from app.services.whatsapp_notifier import WhatsAppNotifierService
                            whatsapp_notifier = WhatsAppNotifierService()
                            await whatsapp_notifier.send_text_message(
                                user["phone"],
                                f"✅ *Deposit Successful!*\n\n"
                                f"Amount: GHS {transaction['amount']}\n"
                                f"Your wallet has been credited.\n\n"
                                f"💰 New Balance: GHS {wallet['balance']}"
                            )
                else:
                    # Wallet was already credited by another process (likely webhook)
                    logging.info(f"Transaction {reference} was already credited by another process")
            
            except ValueError as e:
                # Transaction already processed (idempotency check)
                if "already processed" in str(e).lower() or "already credited" in str(e).lower():
                    return {
                        "status": "success",
                        "message": "Transaction already processed and wallet credited",
                        "paystack_status": paystack_status,
                        "transaction": await transaction_repo.get_by_reference(reference)
                    }
                else:
                    raise
            
            return {
                "status": "success",
                "message": "Transaction verified and wallet credited",
                "paystack_status": paystack_status,
                "transaction": await transaction_repo.get_by_reference(reference)
            }
        elif paystack_status == "failed":
            # Payment failed
            await transaction_repo.update_transaction_status(
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
