import httpx
import logging
from typing import List, Dict
from app.core.config import settings

logger = logging.getLogger(__name__)


class WhatsAppNotifierService:
    """Service for sending WhatsApp messages via Cloud API."""
    
    # Shared client for connection pooling
    _client: httpx.AsyncClient = None
    
    def __init__(self):
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.api_url = settings.WHATSAPP_API_URL
        self.base_url = f"{self.api_url}/{self.phone_number_id}"
        self.flow_mode = settings.WHATSAPP_FLOW_MODE
        
        # Ensure shared client is initialized
        self._ensure_client()
        
    @classmethod
    def _ensure_client(cls):
        """Ensure HTTP client is initialized."""
        if cls._client is None:
            cls._client = httpx.AsyncClient(
                timeout=30.0,
                limits=httpx.Limits(
                    # Use a portion of the total pool for WhatsApp
                    max_keepalive_connections=settings.MAX_KEEPALIVE_CONNECTIONS // 4,
                    max_connections=settings.MAX_CONNECTIONS // 4
                )
            )
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    @classmethod
    async def close_client(cls):
        """Close the shared HTTP client. Should be called on application shutdown."""
        if cls._client is not None:
            await cls._client.aclose()
            cls._client = None
    
    async def send_text_message(
        self,
        phone_number: str,
        text: str
    ) -> bool:
        """
        Send a text message to a WhatsApp user.
        
        Args:
            phone_number: Recipient phone number in E.164 format (e.g., "233XXXXXXXXX")
            text: Message text
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/messages"
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": phone_number,
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": text
                }
            }
            
            response = await self._client.post(
                url,
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("messages") and len(result["messages"]) > 0:
                logger.info(f"Sent WhatsApp message to {phone_number}")
                return True
            else:
                logger.error(f"Failed to send WhatsApp message: {result}")
                return False
                    
        except httpx.HTTPStatusError as e:
            error_msg = "Unknown error"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
            except Exception as json_error:
                logger.warning(f"Failed to parse error response JSON: {json_error}")
                error_msg = str(e)
            
            logger.error(f"Failed to send WhatsApp message to {phone_number}: {error_msg}")
            return False
        except Exception as e:
            logger.error(f"Error sending WhatsApp message to {phone_number}: {str(e)}")
            return False
    
    async def send_interactive_message(
        self,
        phone_number: str,
        text: str,
        buttons: List[Dict[str, str]]
    ) -> bool:
        if not text or not isinstance(text, str):
            logger.error(f"Interactive message text cannot be empty. Phone: {phone_number}")
            return False

        if len(buttons) > 3:
            logger.warning(f"Maximum 3 buttons allowed, got {len(buttons)}. Truncating.")
            buttons = buttons[:3]

        # Ensure each button has valid id/title
        buttons = [
            {"id": str(btn.get("id") or f"btn_{i}"), "title": btn.get("title") or f"Button {i+1}"}
            for i, btn in enumerate(buttons)
        ]

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": text},
                "action": {"buttons": [{"type": "reply", "reply": btn} for btn in buttons]}
            }
        }

        logger.debug(f"Interactive payload: {payload}")

        try:
            response = await self._client.post(
                f"{self.base_url}/messages",
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()
            result = response.json()
            if result.get("messages"):
                logger.info(f"Sent WhatsApp interactive message to {phone_number}")
                return True
            else:
                logger.error(f"Failed to send WhatsApp interactive message: {result}")
                return False

        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("message", str(e))
            except Exception as json_error:
                logger.warning(f"Failed to parse error response JSON: {json_error}")
                error_msg = str(e)
            logger.error(f"Failed to send WhatsApp interactive message to {phone_number}: {error_msg}")
            return False
        except Exception as e:
            logger.error(f"Error sending WhatsApp interactive message to {phone_number}: {str(e)}")
            return False

    
    async def send_list_message(
        self,
        phone_number: str,
        text: str,
        button_text: str,
        sections: List[Dict[str, any]]
    ) -> bool:
        """
        Send a list message (for bundle selection, etc.).
        
        Args:
            phone_number: Recipient phone number in E.164 format
            text: Message text (header)
            button_text: Button text (e.g., "Select Bundle")
            sections: List of sections, each with 'title' and 'rows' (list of items with 'id' and 'title')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/messages"
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": phone_number,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "body": {
                        "text": text
                    },
                    "action": {
                        "button": button_text,
                        "sections": sections
                    }
                }
            }
            
            response = await self._client.post(
                url,
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("messages") and len(result["messages"]) > 0:
                logger.info(f"Sent WhatsApp list message to {phone_number}")
                return True
            else:
                logger.error(f"Failed to send WhatsApp list message: {result}")
                return False
                    
        except httpx.HTTPStatusError as e:
            error_msg = "Unknown error"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
            except Exception as json_error:
                logger.warning(f"Failed to parse error response JSON: {json_error}")
                error_msg = str(e)
            
            logger.error(f"Failed to send WhatsApp list message to {phone_number}: {error_msg}")
            return False
        except Exception as e:
            logger.error(f"Error sending WhatsApp list message to {phone_number}: {str(e)}")
            return False
    
    async def send_admin_alert(self, text: str) -> bool:
        """
        Send an alert to all admin WhatsApp numbers.
        
        Args:
            text: Alert message text
            
        Returns:
            True if sent to at least one admin, False otherwise
        """
        admin_numbers = settings.whatsapp_admin_numbers_list
        
        if not admin_numbers:
            logger.warning("No WhatsApp admin numbers configured")
            return False
        
        success = False
        for admin_number in admin_numbers:
            if await self.send_text_message(admin_number, text):
                success = True
        
        return success

    async def send_flow_message(
        self,
        phone_number: str,
        body_text: str,
        cta_text: str,
        flow_id: str,
        flow_token: str,
        screen_id: str = "NETWORK_SCREEN",
        flow_action: str = "navigate",
        initial_data: dict = None,
    ) -> bool:
        """
        Send a WhatsApp Flows CTA message to open a Flow inside the chat.

        Args:
            phone_number: Recipient phone number in E.164 format
            body_text:    Message body shown before the CTA button
            cta_text:     Label on the CTA button (e.g. "Open Form")
            flow_id:      Meta-assigned Flow ID
            flow_token:   A unique token per flow session (use UUID or phone-based token)
            screen_id:    The initial screen to display (default: NETWORK_SCREEN)
            flow_action:  "navigate" (default) or "data_exchange" for server-driven initial screen
            initial_data: Optional dict of data to pass to the initial screen

        Returns:
            True if successful, False otherwise
        """
        try:
            # Build parameters — flow_action_payload is ONLY valid for
            # "navigate" flows (pointing to a specific starting screen).
            # For "data_exchange" flows it must be omitted entirely or Meta
            # returns error #131009 "Parameter value is not valid".
            parameters: dict = {
                "flow_message_version": "3",
                "flow_token": flow_token,
                "flow_id": flow_id,
                "flow_cta": cta_text,
                "flow_action": flow_action,
                "mode": self.flow_mode,
            }

            if flow_action == "navigate":
                action_payload: dict = {"screen": screen_id}
                if initial_data:
                    action_payload["data"] = initial_data
                parameters["flow_action_payload"] = action_payload

            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": phone_number,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "body": {"text": body_text},
                    "action": {
                        "name": "flow",
                        "parameters": parameters,
                    },
                },
            }


            response = await self._client.post(
                f"{self.base_url}/messages",
                json=payload,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            result = response.json()
            if result.get("messages"):
                logger.info(f"Sent WhatsApp Flow message to {phone_number} (flow_id={flow_id})")
                return True
            else:
                logger.error(f"Failed to send Flow message: {result}")
                return False

        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("message", str(e))
            except Exception:
                error_msg = str(e)
            logger.error(f"HTTP error sending Flow message to {phone_number}: {error_msg}")
            return False
        except Exception as e:
            logger.error(f"Error sending Flow message to {phone_number}: {e}")
            return False


