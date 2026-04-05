import json
import httpx
import logging
from typing import Any, Dict
from app.core.config import settings
from decimal import Decimal, InvalidOperation
from fastapi.responses import PlainTextResponse
from fastapi import APIRouter, Request, Response
from app.services.whatsapp_flows_crypto import (
    decrypt_flow_request,
    encrypt_flow_response,
    FlowDecryptionError,
)
from app.utils.backend_client import BackendAPIClient
from app.services.settings_service import SettingsService
from app.utils.phone_utils import detect_network, normalize_phone_number, validate_phone_number

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Static data
# ---------------------------------------------------------------------------

NETWORKS = [
    {"id": "MTN", "title": "MTN"},
    {"id": "TELECEL", "title": "Telecel"},
    {"id": "AIRTELTIGO", "title": "AirtelTigo"},
]

MOMO_NETWORKS = [
    {"id": "MTN", "title": "MTN MoMo"},
    {"id": "TELECEL", "title": "Telecel Cash"},
    {"id": "AIRTELTIGO", "title": "AirtelTigo Money"},
]

NETWORK_DISPLAY = {
    "MTN": "MTN",
    "TELECEL": "Telecel",
    "AIRTELTIGO": "AirtelTigo",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_bundle(bundle: dict) -> dict:
    """Convert a backend bundle dict to a Flow dropdown option."""
    capacity = bundle.get("capacity", 0)
    if capacity >= 1024:
        cap_str = f"{capacity / 1024:.0f}GB"
    else:
        cap_str = f"{capacity}MB"
    price = bundle.get("price", "?")
    return {
        "id": str(bundle["id"]),
        "title": f"{cap_str} — GHS {price}",
        "description": bundle.get("description", ""),
    }


async def _fetch_bundles(network: str) -> list:
    """Fetch bundles for a network from the backend API."""
    try:
        client = BackendAPIClient.get_client()
        response = await client.get(
            f"{settings.BACKEND_API_URL}/api/v1/bundles",
            params={"network": network},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("bundles", [])
    except Exception as e:
        logger.error(f"Failed to fetch bundles for {network}: {e}")
        return []


def _flow_response(screen: str, data: dict) -> dict:
    """Build a standard next-screen response."""
    return {"screen": screen, "data": data}


def _error_response(message: str) -> dict:
    """Return an error that keeps the user on the current screen."""
    return {
        "screen": "ERROR",
        "data": {
            "error_message": message,
        },
    }


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------

@router.post("")
async def handle_flow_webhook(request: Request) -> Response:
    """
    WhatsApp Flows data-exchange endpoint.
    All comms are AES-128-GCM encrypted (key wrapped with our RSA public key).
    Returns HTTP 421 on decryption failure so Meta refreshes the public key.
    """
    try:
        raw_body = await request.body()
        body = json.loads(raw_body.decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to parse flow request body: {e}")
        return PlainTextResponse("Bad request", status_code=400)

    # -----------------------------------------------------------------------
    # Decrypt
    # -----------------------------------------------------------------------
    try:
        payload, aes_key, iv = decrypt_flow_request(body)
    except FlowDecryptionError as e:
        logger.error(f"Flow decryption failed: {e}")
        # HTTP 421 signals Meta to rotate our public key
        return PlainTextResponse("Decryption failed", status_code=421)

    # -----------------------------------------------------------------------
    # Handle PING (health check from Meta)
    # -----------------------------------------------------------------------
    if payload.get("action") == "ping":
        response_data = {"version": payload.get("version", "3.0"), "data": {"status": "active"}}
        encrypted = encrypt_flow_response(response_data, aes_key, iv)
        return PlainTextResponse(encrypted.decode("utf-8"))

    action  = payload.get("action")
    screen  = payload.get("screen", "")
    data    = payload.get("data", {})
    flow_id = payload.get("flow_id", "")
    version = payload.get("version", "3.0")

    logger.info(f"Flow event | flow_id={flow_id} action={action} screen={screen}")

    # -----------------------------------------------------------------------
    # Route by flow type
    # -----------------------------------------------------------------------
    if flow_id == settings.WHATSAPP_BUY_BUNDLE_FLOW_ID:
        response_data = await _handle_buy_bundle_flow(action, screen, data, version)
    elif flow_id == settings.WHATSAPP_DEPOSIT_FLOW_ID:
        response_data = await _handle_deposit_flow(action, screen, data, version)
    else:
        # Unknown flow — still must respond with valid encrypted body
        logger.warning(f"Unknown flow_id: {flow_id}")
        response_data = {"version": version, "screen": "ERROR", "data": {"error_message": "Unknown flow"}}

    # -----------------------------------------------------------------------
    # Encrypt and return
    # -----------------------------------------------------------------------
    encrypted = encrypt_flow_response(response_data, aes_key, iv)
    return PlainTextResponse(encrypted.decode("utf-8"))


# ---------------------------------------------------------------------------
# Buy Bundle Flow handlers
# ---------------------------------------------------------------------------

async def _handle_buy_bundle_flow(action: str, screen: str, data: dict, version: str) -> dict:
    """Route Buy Bundle flow events to the correct handler."""

    if action == "INIT":
        # Entry point — show network selection with static data
        return {
            "version": version,
            **_flow_response("NETWORK_SCREEN", {"networks": NETWORKS}),
        }

    if action == "data_exchange":
        if screen == "NETWORK_SCREEN":
            return await _bundle_flow_get_bundles(data, version)
        if screen == "PHONE_SCREEN":
            return await _bundle_flow_validate_phone(data, version)

    if action == "BACK":
        # Refresh the screen the user is returning to
        if screen == "BUNDLE_SCREEN":
            return await _bundle_flow_get_bundles(data, version)
        if screen == "NETWORK_SCREEN":
            return {
                "version": version,
                **_flow_response("NETWORK_SCREEN", {"networks": NETWORKS}),
            }

    logger.warning(f"Unhandled buy_bundle action={action} screen={screen}")
    return {"version": version, **_error_response("Unexpected error. Please try again.")}


async def _bundle_flow_get_bundles(data: dict, version: str) -> dict:
    """Fetch bundles for the selected network and navigate to BUNDLE_SCREEN."""
    network = data.get("selected_network", "")
    if not network:
        return {"version": version, **_error_response("Please select a network.")}

    bundles_raw = await _fetch_bundles(network)
    if not bundles_raw:
        return {
            "version": version,
            **_error_response(f"No bundles available for {NETWORK_DISPLAY.get(network, network)}. Please try later."),
        }

    bundles = [_fmt_bundle(b) for b in bundles_raw]

    return {
        "version": version,
        **_flow_response(
            "BUNDLE_SCREEN",
            {
                "network_name": NETWORK_DISPLAY.get(network, network),
                "bundles": bundles,
                "selected_network": network,
            },
        ),
    }


async def _bundle_flow_validate_phone(data: dict, version: str) -> dict:
    """
    Validate recipient phone after PHONE_SCREEN submission.
    If valid, navigate to the CONFIRM_SCREEN with order summary.
    """
    selected_network = data.get("selected_network", "")
    selected_bundle_id = data.get("selected_bundle_id", "")
    recipient_phone = data.get("recipient_phone", "").strip()
    bundles_list = data.get("bundles", [])
    network_name = data.get("network_name", selected_network)
    bundle_summary = data.get("bundle_summary", "")

    # Validate phone
    is_valid, error_msg = validate_phone_number(recipient_phone)
    if not is_valid:
        return {"version": version, **_error_response(f"❌ {error_msg}")}

    # Detect and match network
    detected_network = detect_network(recipient_phone)
    if not detected_network:
        return {
            "version": version,
            **_error_response(
                "Could not detect network. Supported: MTN (024/054/055/059/053), "
                "Telecel (020/050), AirtelTigo (026/027/056/057)."
            ),
        }
    if detected_network != selected_network:
        detected_name = NETWORK_DISPLAY.get(detected_network, detected_network)
        selected_name = NETWORK_DISPLAY.get(selected_network, selected_network)
        return {
            "version": version,
            **_error_response(
                f"Number belongs to {detected_name}, but you selected a {selected_name} bundle. "
                f"Please enter a {selected_name} number."
            ),
        }

    # Look up the bundle title for the summary
    if not bundle_summary:
        for b in bundles_list:
            if str(b.get("id")) == str(selected_bundle_id):
                bundle_summary = b.get("title", selected_bundle_id)
                break

    # Extract price from the title (e.g. "1GB — GHS 5.00")
    summary_price = "N/A"
    if "GHS" in bundle_summary:
        try:
            summary_price = "GHS " + bundle_summary.split("GHS")[-1].strip()
        except Exception:
            pass

    normalized_phone = normalize_phone_number(recipient_phone)

    return {
        "version": version,
        **_flow_response(
            "CONFIRM_SCREEN",
            {
                "summary_network": NETWORK_DISPLAY.get(selected_network, selected_network),
                "summary_bundle":  bundle_summary,
                "summary_phone":   normalized_phone,
                "summary_price":   summary_price,
                "selected_network":   selected_network,
                "selected_bundle_id": selected_bundle_id,
                "recipient_phone":    normalized_phone,
            },
        ),
    }


# ---------------------------------------------------------------------------
# Deposit Flow handlers
# ---------------------------------------------------------------------------

async def _handle_deposit_flow(action: str, screen: str, data: dict, version: str) -> dict:
    """Route Deposit flow events to the correct handler."""

    if action == "INIT":
        settings_service = SettingsService()
        try:
            min_deposit = float(await settings_service.get_min_deposit_amount())
            max_deposit = float(await settings_service.get_max_deposit_amount())
        except Exception:
            min_deposit = float(settings.MINIMUM_DEPOSIT_AMOUNT)
            max_deposit = float(settings.MAXIMUM_DEPOSIT_AMOUNT)

        return {
            "version": version,
            **_flow_response(
                "AMOUNT_SCREEN",
                {"min_amount": min_deposit, "max_amount": max_deposit},
            ),
        }

    if action == "data_exchange":
        if screen == "AMOUNT_SCREEN":
            return await _deposit_flow_validate_amount(data, version)

    if action == "BACK":
        if screen == "AMOUNT_SCREEN":
            return await _handle_deposit_flow("INIT", screen, data, version)

    logger.warning(f"Unhandled deposit action={action} screen={screen}")
    return {"version": version, **_error_response("Unexpected error. Please try again.")}


async def _deposit_flow_validate_amount(data: dict, version: str) -> dict:
    """Validate the deposit amount and navigate to PHONE_SCREEN."""

    amount_str = str(data.get("deposit_amount", "")).strip()

    try:
        amount = Decimal(amount_str)
    except (InvalidOperation, ValueError):
        return {"version": version, **_error_response("Invalid amount. Please enter a number (e.g. 20).")}

    # Fetch limits
    settings_service = SettingsService()
    try:
        min_deposit = Decimal(str(await settings_service.get_min_deposit_amount()))
        max_deposit = Decimal(str(await settings_service.get_max_deposit_amount()))
    except Exception:
        min_deposit = Decimal(str(settings.MINIMUM_DEPOSIT_AMOUNT))
        max_deposit = Decimal(str(settings.MAXIMUM_DEPOSIT_AMOUNT))

    if amount < min_deposit:
        return {
            "version": version,
            **_error_response(f"Minimum deposit is GHS {min_deposit}. Please enter a higher amount."),
        }
    if amount > max_deposit:
        return {
            "version": version,
            **_error_response(f"Maximum deposit is GHS {max_deposit}. Please enter a lower amount."),
        }

    return {
        "version": version,
        **_flow_response(
            "PHONE_SCREEN",
            {
                "deposit_amount": str(amount),
                "networks": MOMO_NETWORKS,
            },
        ),
    }
