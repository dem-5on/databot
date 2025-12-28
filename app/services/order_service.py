from app.services.notifier import NotifierService
from app.repository.order_repo import OrderRepository
from app.services.wallet_service import WalletService
from app.repository.bundle_repo import BundleRepository
from app.services.blessdatahub_client import BlessdatahubClient
from app.services.referral_service import ReferralService
from app.repository.transaction_repo import TransactionRepository
from app.core.constants import TransactionType, TransactionStatus, OrderStatus


class OrderService:
    """Service for order operations using Supabase."""

    def __init__(self):
        self.blessdatahub_client = BlessdatahubClient()
        self.bundle_repo = BundleRepository()
        self.order_repo = OrderRepository()
        self.transaction_repo = TransactionRepository()
        self.wallet_service = WalletService()
        self.referral_service = ReferralService()
        self.notifier = NotifierService()

    async def create_order(
        self,
        user_id: str,
        bundle_id: str,
        phone: str
    ) -> dict:
        """
        Create an order and process bundle purchase.
        
        Args:
            user_id: User ID
            bundle_id: Bundle ID
            phone: Target phone number for bundle
            
        Returns:
            Created order
            
        Raises:
            ValueError: If bundle not found, insufficient balance, or vendor failure
        """
        # Get bundle
        bundle = await self.bundle_repo.get_by_id(bundle_id)
        if not bundle or not bundle.get("active"):
            await self.notifier.send_admin_alert(f"Bundle not found or inactive. Bundle ID: {bundle_id}")
            raise ValueError(f"Bundle not found or inactive: {bundle_id}")

        bundle_price = float(bundle["price"])
        
        # Check wallet balance
        wallet_balance = await self.wallet_service.get_balance(user_id)
        if wallet_balance < bundle_price:
            await self.notifier.send_admin_alert(f"<b>User: {user_id}</b>\n\nInsufficient balance. Account balance is : GHS{wallet_balance}, Require: GHS{bundle_price} to purchase {bundle['network']} {bundle['capacity']}GB bundle.")
            raise ValueError(f"Insufficient balance. Available: GHS{wallet_balance}, Required: GHS{bundle_price}")
        
        # Create order
        order = await self.order_repo.create_order(
            user_id=user_id,
            bundle_id=bundle_id,
            phone=phone,
            price=bundle_price,
            status=OrderStatus.PROCESSING.value
        )
        
        # Create transaction record
        transaction = await self.transaction_repo.create_transaction(
            user_id=user_id,
            transaction_type=TransactionType.PURCHASE.value,
            amount=bundle_price,
            currency="GHS",
            reference=f"ORDER-{order['id']}",
            status=TransactionStatus.PROCESSING.value,
            phone=phone,
            provider=bundle["network"]
        )
        
        try:
            # Debit wallet
            await self.wallet_service.debit_wallet(user_id, bundle_price)
            
            # Purchase bundle from DatamartGH
            try:
                vendor_response = await self.blessdatahub_client.purchase_bundle(
                    phone_number=phone,
                    network=bundle["network"],
                    package_size=f"{bundle['capacity']}GB",
                    ref=order["id"]
                )
                
                # Success - update order and transaction
                # Blessdatahub returns order_ids array
                order_ids = vendor_response.get("order_ids", [])
                vendor_ref = str(order_ids[0]) if order_ids else ""
                await self.order_repo.update_order_status(
                    order["id"],
                    OrderStatus.SUCCESS.value,
                    vendor_reference=vendor_ref,
                    vendor_response=vendor_response
                )
                
                await self.transaction_repo.update_transaction_status(
                    transaction["id"],
                    TransactionStatus.SUCCESS.value,
                    raw_payload=vendor_response
                )
                
                # Get updated order
                order = await self.order_repo.get_by_id(order["id"])
                
                # Award referral bonus if this is user's first successful transaction
                await self.referral_service.award_referral_bonus(user_id)
                
                return order
                
            except Exception as vendor_error:
                # Vendor failure - refund wallet
                await self.wallet_service.refund_wallet(
                    user_id=user_id,
                    amount=bundle_price,
                    transaction_id=transaction["id"]
                )
                
                # Update order and transaction status
                await self.order_repo.update_order_status(
                    order["id"],
                    OrderStatus.FAILED.value,
                    vendor_response={"error": str(vendor_error)}
                )
                
                await self.transaction_repo.update_transaction_status(
                    transaction["id"],
                    TransactionStatus.FAILED.value,
                    raw_payload={"error": str(vendor_error)}
                )
                
                # Notify admin
                await self.notifier.send_admin_alert(
                    f"❌ Order Failure\n"
                    f"User: {user_id}\n"
                    f"Order ID: {order['id']}\n"
                    f"Bundle: {bundle['network']} {bundle['capacity']}GB\n"
                    f"Error: {str(vendor_error)}"
                )
                
                raise ValueError(f"Vendor purchase failed: {str(vendor_error)}")
                
        except ValueError as e:
            # Re-raise balance errors
            raise
        except Exception as e:
            # Other errors
            raise ValueError(f"Order creation failed: {str(e)}")
