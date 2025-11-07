from sqlalchemy import select
from app.models.bundle import Bundle
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import UUID
from app.models.order import Order, OrderStatus
from app.services.notifier import NotifierService
from app.services.wallet_service import WalletService
from app.services.datamart_client import DatamartClient
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from uuid import UUID as UUIDType


class OrderService:
    """Service for order operations."""

    def __init__(self):
        self.datamart_client = DatamartClient()

    async def create_order(
        self,
        db: AsyncSession,
        user_id: UUIDType,
        bundle_id: UUIDType,
        phone: str
    ) -> Order:
        """
        Create an order and process bundle purchase.
        
        Args:
            db: Database session
            user_id: User ID
            bundle_id: Bundle ID
            phone: Target phone number for bundle
            
        Returns:
            Created order
            
        Raises:
            ValueError: If bundle not found, insufficient balance, or vendor failure
        """
        # Get bundle - convert bundle_id to string since Bundle.id is stored as string
        bundle_id_str = str(bundle_id)
        bundle_stmt = select(Bundle).where(Bundle.id == bundle_id_str, Bundle.active == True)
        bundle_result = await db.execute(bundle_stmt)
        bundle = bundle_result.scalar_one_or_none()
        
        if not bundle:
            raise ValueError(f"Bundle not found or inactive. Bundle ID: {bundle_id_str}")
        
        # Check wallet balance
        wallet_balance = await WalletService.get_balance(db, user_id)
        if wallet_balance < bundle.price:
            raise ValueError(f"Insufficient balance. Available: {wallet_balance}, Required: {bundle.price}")
        
        # Create order
        # Convert bundle_id to UUID for Order model (which uses as_uuid=True)
        # Bundle.id is stored as string, but Order.bundle_id expects UUID
        try:
            if isinstance(bundle_id, str):
                bundle_uuid = UUIDType(bundle_id)
            else:
                bundle_uuid = bundle_id
        except (ValueError, TypeError):
            bundle_uuid = UUIDType(bundle_id_str)
        
        # Also convert user_id if it's a string
        try:
            if isinstance(user_id, str):
                user_uuid = UUIDType(user_id)
            else:
                user_uuid = user_id
        except (ValueError, TypeError):
            user_uuid = user_id
        
        order = Order(
            user_id=user_uuid,
            bundle_id=bundle_uuid,
            phone=phone,
            price=bundle.price,
            status=OrderStatus.PROCESSING
        )
        db.add(order)
        await db.flush()  # Get order ID
        
        # Create transaction record
        transaction = Transaction(
            user_id= str(user_id),
            type=TransactionType.PURCHASE,
            amount=bundle.price,
            currency="GHS",
            reference=f"ORDER-{order.id}",
            status=TransactionStatus.PROCESSING,
            phone=phone,
            provider=bundle.network
        )
        db.add(transaction)
        await db.flush()
        
        try:
            # Debit wallet (atomic operation)
            wallet = await WalletService.debit_wallet(db, user_id, bundle.price)
            
            # Purchase bundle from DatamartGH
            try:
                # Map network to DatamartGH format
                network_map = {
                    "MTN": "YELLO",
                    "VODAFONE": "TELECEL",
                    "AIRTELTIGO": "AT_PREMIUM"
                }
                datamart_network = network_map.get(bundle.network, "YELLO")
                
                vendor_response = await self.datamart_client.purchase_bundle(
                    phone_number=phone,
                    network=bundle.network,  # Client will map it
                    capacity=bundle.capacity,
                    ref=str(order.id)
                )
                
                # Success - update order and transaction
                vendor_ref = vendor_response.get("transactionReference", "")
                order.status = OrderStatus.SUCCESS
                order.vendor_reference = vendor_ref
                order.vendor_response = vendor_response
                
                transaction.status = TransactionStatus.SUCCESS
                transaction.raw_payload = vendor_response
                
                await db.commit()
                
                # Award referral bonus if this is user's first successful transaction
                from app.services.referral_service import ReferralService
                await ReferralService.award_referral_bonus(db, user_id)
                
                return order
                
            except Exception as vendor_error:
                # Vendor failure - refund wallet
                await WalletService.refund_wallet(
                    db=db,
                    user_id=user_uuid,
                    amount=bundle.price,
                    transaction_id=transaction.id
                )
                
                # Update order and transaction status
                order.status = OrderStatus.FAILED
                order.vendor_response = {"error": str(vendor_error)}
                
                transaction.status = TransactionStatus.FAILED
                transaction.raw_payload = {"error": str(vendor_error)}
                
                await db.commit()
                
                # Notify admin
                await NotifierService.send_admin_alert(
                    f"❌ Order Failure\n"
                    f"User: {user_id}\n"
                    f"Order ID: {order.id}\n"
                    f"Bundle: {bundle.network} {bundle.capacity}GB\n"
                    f"Error: {str(vendor_error)}"
                )
                
                raise ValueError(f"Vendor purchase failed: {str(vendor_error)}")
                
        except ValueError as e:
            # Re-raise balance errors
            await db.rollback()
            raise
        except Exception as e:
            # Other errors
            await db.rollback()
            raise ValueError(f"Order creation failed: {str(e)}")

