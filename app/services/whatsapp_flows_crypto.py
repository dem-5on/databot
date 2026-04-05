"""
WhatsApp Flows Encryption / Decryption Service
===============================================
Implements the Meta Flows Data Exchange encryption protocol:
  - Incoming: RSA-OAEP (SHA-256) to unwrap AES key + AES-128-GCM to decrypt payload
  - Outgoing: AES-128-GCM with bit-flipped IV to encrypt response

"""

import json
import logging
from typing import Tuple
from app.core.config import settings
from base64 import b64decode, b64encode
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding

logger = logging.getLogger(__name__)


class FlowDecryptionError(Exception):
    """Raised when the encrypted payload cannot be decrypted.
    
    The caller should return HTTP 421 to signal Meta to refresh the public key.
    """
    pass


def _load_private_key():
    """Load the RSA private key from settings."""
    raw = settings.WHATSAPP_FLOW_PRIVATE_KEY
    if not raw:
        raise FlowDecryptionError("WHATSAPP_FLOW_PRIVATE_KEY is not configured")
    
    # Support both literal newlines and escaped \n in .env
    pem = raw.replace("\\n", "\n").encode("utf-8")
    try:
        return serialization.load_pem_private_key(pem, password=None, backend=default_backend())
    except Exception as e:
        raise FlowDecryptionError(f"Failed to load RSA private key: {e}") from e


def decrypt_flow_request(body: dict) -> Tuple[dict, bytes, bytes]:
    """
    Decrypt an incoming WhatsApp Flows data exchange request.

    Args:
        body: Parsed JSON body with keys:
              - encrypted_flow_data (base64)
              - encrypted_aes_key (base64)
              - initial_vector (base64)

    Returns:
        Tuple of (decrypted_payload: dict, aes_key: bytes, iv: bytes)
        The aes_key and iv are returned so we can encrypt the response.

    Raises:
        FlowDecryptionError: If anything in the decryption chain fails.
                             Caller must return HTTP 421.
    """
    try:
        encrypted_flow_data = b64decode(body["encrypted_flow_data"])
        encrypted_aes_key   = b64decode(body["encrypted_aes_key"])
        iv                  = b64decode(body["initial_vector"])
    except (KeyError, Exception) as e:
        raise FlowDecryptionError(f"Missing or invalid base64 fields in request body: {e}") from e

    # Step 1 — Decrypt the AES key with our RSA private key (OAEP + SHA-256)
    try:
        private_key = _load_private_key()
        aes_key = private_key.decrypt(
            encrypted_aes_key,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    except FlowDecryptionError:
        raise
    except Exception as e:
        raise FlowDecryptionError(f"RSA decryption of AES key failed: {e}") from e

    # Step 2 — Decrypt the flow data with AES-128-GCM
    # The last 16 bytes of the ciphertext are the GCM auth tag
    try:
        ciphertext = encrypted_flow_data[:-16]
        auth_tag   = encrypted_flow_data[-16:]

        decryptor = Cipher(
            algorithms.AES(aes_key),
            modes.GCM(iv, auth_tag),
            backend=default_backend(),
        ).decryptor()

        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        payload = json.loads(plaintext.decode("utf-8"))
    except Exception as e:
        raise FlowDecryptionError(f"AES-GCM decryption failed: {e}") from e

    logger.debug(f"Decrypted flow payload action={payload.get('action')} screen={payload.get('screen')}")
    return payload, aes_key, iv


def encrypt_flow_response(response: dict, aes_key: bytes, request_iv: bytes) -> bytes:
    """
    Encrypt a response to send back to WhatsApp Flows.

    The response IV is the bitwise complement (flip) of the request IV.
    Returns raw bytes (base64-encoded by convention, but Meta expects the raw
    base64 string as the response body with Content-Type text/plain).

    Args:
        response:   Response dict to encrypt
        aes_key:    The AES key from the decrypted request
        request_iv: The IV from the decrypted request

    Returns:
        Base64-encoded bytes ready to send as the HTTP response body
    """
    # Flip every bit of the request IV for the response
    flipped_iv = bytes([b ^ 0xFF for b in request_iv])

    plaintext = json.dumps(response).encode("utf-8")

    encryptor = Cipher(
        algorithms.AES(aes_key),
        modes.GCM(flipped_iv),
        backend=default_backend(),
    ).encryptor()

    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    auth_tag   = encryptor.tag  # 16 bytes

    # Return base64(ciphertext + auth_tag)
    return b64encode(ciphertext + auth_tag)
