import logging
from typing import Dict, Tuple, Optional, Any
from app.utils.phone_utils import normalize_phone_number
from app.services.whatsapp_notifier import WhatsAppNotifierService
from whatsapp.keyboard import get_main_menu_buttons, get_main_menu_buttons_extended
import whatsapp.handlers.balance as balance
import whatsapp.handlers.deposit as deposit
import whatsapp.handlers.bundles as bundles
import whatsapp.handlers.history as history
import whatsapp.handlers.referral as referral
import whatsapp.handlers.help as help
import whatsapp.handlers.start as start

logger = logging.getLogger(__name__)


class WhatsAppBot:
    """WhatsApp bot with conversation state management."""
    
    # Conversation states
    STATE_NONE = "none"
    STATE_DEPOSIT_AMOUNT = "deposit_amount"
    STATE_DEPOSIT_PHONE = "deposit_phone"
    STATE_DEPOSIT_OTP = "deposit_otp"
    STATE_BUNDLES_NETWORK = "bundles_network"
    STATE_BUNDLES_BUNDLE = "bundles_bundle"
    STATE_BUNDLES_PHONE = "bundles_phone"
    
    def __init__(self):
        self.notifier = WhatsAppNotifierService()
        # In-memory state storage (phone_number -> (state, data))
        # In production, consider using Redis or database for state persistence
        self.user_states: Dict[str, Tuple[str, Dict[str, Any]]] = {}
    
    def set_user_state(self, phone_number: str, state: str, data: Optional[Dict[str, Any]] = None):
        """
        Set user conversation state.
        
        Args:
            phone_number: User's phone number
            state: State name
            data: Optional state data. If None, preserves existing data when changing state.
        """
        normalized_phone = normalize_phone_number(phone_number)
        if data is None:
            # Preserve existing data when only state is being changed
            _, existing_data = self.get_user_state(normalized_phone)
            data = existing_data
        self.user_states[normalized_phone] = (state, data or {})
        logger.debug(f"Set state for {normalized_phone}: {state}, data keys: {list((data or {}).keys())}")
    
    def get_user_state(self, phone_number: str) -> Tuple[str, Dict[str, Any]]:
        """
        Get user conversation state.
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Tuple of (state, data)
        """
        normalized_phone = normalize_phone_number(phone_number)
        return self.user_states.get(normalized_phone, (self.STATE_NONE, {}))
    
    def clear_user_state(self, phone_number: str):
        """
        Clear user conversation state.
        
        Args:
            phone_number: User's phone number
        """
        normalized_phone = normalize_phone_number(phone_number)
        if normalized_phone in self.user_states:
            del self.user_states[normalized_phone]
            logger.debug(f"Cleared state for {normalized_phone}")
    
    def update_user_state_data(self, phone_number: str, **kwargs):
        """
        Update user state data without changing state.
        
        Args:
            phone_number: User's phone number
            **kwargs: Data to update
        """
        normalized_phone = normalize_phone_number(phone_number)
        state, data = self.get_user_state(normalized_phone)
        data.update(kwargs)
        self.set_user_state(normalized_phone, state, data)

    async def send_main_menu(self, phone_number: str, primary_text: str, secondary_text: str = "More options:") -> None:
        """Send main menu buttons (two rows) to the user."""
        normalized_phone = normalize_phone_number(phone_number)
        await self.notifier.send_interactive_message(
            normalized_phone,
            primary_text,
            get_main_menu_buttons()
        )
        await self.notifier.send_interactive_message(
            normalized_phone,
            secondary_text,
            get_main_menu_buttons_extended()
        )
    
    async def handle_webhook_event(self, event: Dict[str, Any]) -> None:
        """
        Handle incoming webhook event from WhatsApp.
        
        Args:
            event: Webhook event dictionary
        """
        try:
            # Handle messages
            if "messages" in event:
                for message in event["messages"]:
                    await self._handle_message(message)
            
            # Handle status updates (optional)
            if "statuses" in event:
                for status in event["statuses"]:
                    await self._handle_status_update(status)
                    
        except Exception as e:
            logger.error(f"Error handling webhook event: {str(e)}", exc_info=True)
    
    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """
        Handle incoming message.
        
        Args:
            message: Message dictionary from webhook
        """
        try:
            from_phone = message.get("from")
            message_id = message.get("id")
            message_type = message.get("type")
            
            if not from_phone:
                logger.warning("Message missing 'from' field")
                return
            
            # Handle interactive button responses
            if message_type == "interactive":
                interactive = message.get("interactive", {})
                interactive_type = interactive.get("type")
                
                if interactive_type == "button_reply":
                    button_id = interactive.get("button_reply", {}).get("id")
                    await self.process_button_click(from_phone, button_id, message_id)
                elif interactive_type == "list_reply":
                    list_id = interactive.get("list_reply", {}).get("id")
                    await self.process_button_click(from_phone, list_id, message_id)
                return
            
            # Handle text messages
            if message_type == "text":
                text = message.get("text", {}).get("body", "").strip()
                await self.process_message(from_phone, text, message_id)
            else:
                logger.info(f"Unhandled message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
    
    async def _handle_status_update(self, status: Dict[str, Any]) -> None:
        """
        Handle message status update (delivery receipt, etc.).
        
        Args:
            status: Status update dictionary
        """
        # Log status updates for debugging
        status_type = status.get("status")
        message_id = status.get("id")
        logger.debug(f"Message {message_id} status: {status_type}")
    
    async def process_message(self, phone_number: str, message_text: str, message_id: str) -> None:
        """
        Process text message from user.
        
        Args:
            phone_number: User's phone number
            message_text: Message text
            message_id: WhatsApp message ID
        """
        try:
            normalized_phone = normalize_phone_number(phone_number)
            state, state_data = self.get_user_state(normalized_phone)
            
            # Normalize message text for command matching
            text_lower = message_text.lower().strip()
            
            # Handle menu commands (always available)
            # Check if message contains a referral code (e.g., "hi REFCODE", "start REFCODE", or "start=REFCODE")
            referral_code = None
            
            # Handle "start=REFCODE" format (from referral link)
            if "start=" in text_lower:
                try:
                    # Extract code from "start=REFCODE" format
                    # Handle both "start=REFCODE" and "start=REFCODE " (with trailing text)
                    start_part = text_lower.split("start=", 1)[1].strip()
                    # Extract first word/token (8 characters for referral code)
                    code_part = start_part.split()[0] if start_part.split() else start_part[:8]
                    # Take exactly 8 characters
                    if len(code_part) >= 8:
                        potential_code = code_part[:8].upper()
                        if len(potential_code) == 8 and potential_code.isalnum():
                            referral_code = potential_code
                            text_lower = "start"  # Treat as start command
                except (IndexError, ValueError):
                    pass
            
            # Handle space-separated format (e.g., "hi REFCODE" or "start REFCODE")
            if not referral_code and text_lower.startswith(("hi ", "hello ", "start ", "menu ")):
                parts = message_text.strip().split(maxsplit=1)
                if len(parts) > 1:
                    # Check if second part looks like a referral code (8 alphanumeric characters)
                    potential_code = parts[1].strip().upper()
                    if len(potential_code) == 8 and potential_code.isalnum():
                        referral_code = potential_code
                        # Use the command part only (e.g., "hi")
                        text_lower = parts[0].lower().strip()
            
            if text_lower in ["hi", "hello", "start", "menu", "help"]:
                await start.start_handler(normalized_phone, self, referral_code=referral_code)
                return
            
            # Route based on state
            if state == self.STATE_DEPOSIT_AMOUNT:
                await deposit.handle_amount(normalized_phone, message_text, self)
            elif state == self.STATE_DEPOSIT_PHONE:
                await deposit.handle_phone(normalized_phone, message_text, self)
            elif state == self.STATE_DEPOSIT_OTP:
                await deposit.handle_otp(normalized_phone, message_text, self)
            elif state == self.STATE_BUNDLES_PHONE:
                await bundles.handle_phone(normalized_phone, message_text, self)
            else:
                # No active state, treat as command
                if text_lower in ["balance", "bal"]:
                    await balance.balance_handler(normalized_phone, self)
                elif text_lower in ["deposit", "dep"]:
                    await deposit.start(normalized_phone, self)
                elif text_lower in ["bundles", "bundle"]:
                    await bundles.start(normalized_phone, self)
                elif text_lower in ["history", "hist"]:
                    await history.history_handler(normalized_phone, self)
                elif text_lower in ["referral", "ref"]:
                    await referral.referral_handler(normalized_phone, self)
                elif text_lower == "help":
                    await help.help_handler(normalized_phone, self)
                else:
                    # Unknown command, show start menu
                    await start.start_handler(normalized_phone, self)
                    
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            await self.notifier.send_text_message(
                normalized_phone,
                "❌ An error occurred. Please try again or type 'help' for assistance."
            )
    
    async def process_button_click(self, phone_number: str, button_id: str, message_id: str) -> None:
        """
        Process button click from user.
        
        Args:
            phone_number: User's phone number
            button_id: Button ID that was clicked
            message_id: WhatsApp message ID
        """
        try:
            normalized_phone = normalize_phone_number(phone_number)
            
            # Handle main menu buttons
            if button_id == "menu_balance":
                await balance.balance_handler(normalized_phone, self)
            elif button_id == "menu_deposit":
                await deposit.start(normalized_phone, self)
            elif button_id == "menu_bundles":
                await bundles.start(normalized_phone, self)
            elif button_id == "menu_history":
                await history.history_handler(normalized_phone, self)
            elif button_id == "menu_referral":
                await referral.referral_handler(normalized_phone, self)
            elif button_id == "menu_help":
                await help.help_handler(normalized_phone, self)
            
            # Handle network selection
            elif button_id.startswith("network_"):
                network = button_id.replace("network_", "")
                await bundles.handle_network(normalized_phone, network, self)
            
            # Handle bundle selection
            elif button_id.startswith("bundle_"):
                bundle_id = button_id.replace("bundle_", "")
                await bundles.handle_bundle(normalized_phone, bundle_id, self)
            
            # Handle navigation
            elif button_id == "back":
                state, _ = self.get_user_state(normalized_phone)
                if state == self.STATE_BUNDLES_BUNDLE:
                    await bundles.start(normalized_phone, self)
                elif state == self.STATE_BUNDLES_PHONE:
                    bundle_id = self.get_user_state(normalized_phone)[1].get("selected_bundle_id")
                    if bundle_id:
                        await bundles.handle_bundle(normalized_phone, bundle_id, self)
                    else:
                        await bundles.start(normalized_phone, self)
                else:
                    await start.start_handler(normalized_phone, self)
            
            elif button_id == "cancel":
                self.clear_user_state(normalized_phone)
                await self.notifier.send_text_message(
                    normalized_phone,
                    "❌ Operation cancelled. Type 'menu' to see options."
                )
            
            else:
                logger.warning(f"Unknown button ID: {button_id}")
                await start.start_handler(normalized_phone, self)
                
        except Exception as e:
            logger.error(f"Error processing button click: {str(e)}", exc_info=True)
            await self.notifier.send_text_message(
                normalized_phone,
                "❌ An error occurred. Please try again or type 'help' for assistance."
            )



