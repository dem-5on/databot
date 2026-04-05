#!/usr/bin/env python3
"""
WhatsApp Flows Management CLI
==============================
Handles the full lifecycle of WhatsApp Flows:
  - RSA key pair generation
  - Uploading public key to Meta
  - Creating / updating flows via Meta API
  - Publishing flows (manual step before going live)
  - Listing existing flows

Usage:
  python scripts/manage_flows.py --generate-keys
  python scripts/manage_flows.py --upload-key
  python scripts/manage_flows.py --list-flows
  python scripts/manage_flows.py --create-flow --flow-name "Buy Bundle" --flow-file whatsapp/flows/buy_bundle_flow.json
  python scripts/manage_flows.py --publish-flow --flow-id <FLOW_ID>
  python scripts/manage_flows.py --get-flow --flow-id <FLOW_ID>
  python scripts/manage_flows.py --delete-flow --flow-id <FLOW_ID>

Prerequisites:
  pip install cryptography requests python-dotenv
  Set WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env
"""

import os
import sys
import json
import argparse
import textwrap

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not found — reading env vars from shell only")

try:
    import requests
except ImportError:
    print("❌ 'requests' is not installed. Run: pip install requests")
    sys.exit(1)

try:
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
except ImportError:
    print("❌ 'cryptography' is not installed. Run: pip install cryptography")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _require_env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        print(f"❌ Environment variable {name} is not set. Add it to your .env file.")
        sys.exit(1)
    return val


def _get_api_base() -> str:
    api_url = os.environ.get("WHATSAPP_API_URL", "https://graph.facebook.com/v18.0")
    phone_id = _require_env("WHATSAPP_PHONE_NUMBER_ID")
    return f"{api_url}/{phone_id}"


def _get_waba_id() -> str:
    """WhatsApp Business Account ID — needed for flow creation."""
    waba_id = os.environ.get("WHATSAPP_WABA_ID", "").strip()
    if not waba_id:
        print("⚠️  WHATSAPP_WABA_ID not set. You may need it to create flows.")
    return waba_id


def _auth_header() -> dict:
    token = _require_env("WHATSAPP_ACCESS_TOKEN")
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Generate RSA Key Pair
# ---------------------------------------------------------------------------

def generate_keys(output_dir: str = ".") -> None:
    """
    Generate a 2048-bit RSA key pair and save them to files.
    The private key goes into your .env as WHATSAPP_FLOW_PRIVATE_KEY.
    The public key is uploaded to Meta.
    """
    print("🔑 Generating 2048-bit RSA key pair...")

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    # Serialize private key (PKCS8 PEM, no password)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    # Serialize public key (SubjectPublicKeyInfo PEM)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    priv_path = os.path.join(output_dir, "flows_private_key.pem")
    pub_path  = os.path.join(output_dir, "flows_public_key.pem")

    with open(priv_path, "w") as f:
        f.write(private_pem)
    with open(pub_path, "w") as f:
        f.write(public_pem)

    print(f"✅ Private key saved: {priv_path}")
    print(f"✅ Public key saved:  {pub_path}")
    print()
    print("─" * 60)
    print("Next steps:")
    print()
    print("1. Add the private key to your .env file (escape newlines as \\n):")
    print()

    # Print the env-friendly version
    env_value = private_pem.replace("\n", "\\n")
    print(f'   WHATSAPP_FLOW_PRIVATE_KEY="{env_value}"')
    print()
    print("2. Upload the public key to Meta:")
    print(f"   python scripts/manage_flows.py --upload-key --key-file {pub_path}")
    print("─" * 60)


# ---------------------------------------------------------------------------
# 2. Upload Public Key to Meta
# ---------------------------------------------------------------------------

def upload_public_key(key_file: str | None = None) -> None:
    """Upload the RSA public key to Meta so they can encrypt the AES key."""
    if key_file:
        with open(key_file) as f:
            public_key_pem = f.read().strip()
    else:
        # Try to derive public key from the private key in env
        private_pem_raw = os.environ.get("WHATSAPP_FLOW_PRIVATE_KEY", "").replace("\\n", "\n").strip()
        if not private_pem_raw:
            print("❌ Provide --key-file or set WHATSAPP_FLOW_PRIVATE_KEY in .env")
            sys.exit(1)
        private_key = serialization.load_pem_private_key(
            private_pem_raw.encode(), password=None, backend=default_backend()
        )
        public_key_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

    phone_id = _require_env("WHATSAPP_PHONE_NUMBER_ID")
    api_url  = os.environ.get("WHATSAPP_API_URL", "https://graph.facebook.com/v18.0")
    url      = f"{api_url}/{phone_id}/whatsapp_business_encryption"

    print(f"⬆️  Uploading public key to Meta ({url})...")

    response = requests.post(
        url,
        headers={**_auth_header(), "Content-Type": "application/json"},
        json={"business_public_key": public_key_pem},
    )

    if response.ok:
        result = response.json()
        print(f"✅ Public key uploaded successfully!")
        print(f"   Response: {json.dumps(result, indent=2)}")
    else:
        print(f"❌ Failed to upload public key: HTTP {response.status_code}")
        print(f"   Response: {response.text}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# 3. List Flows
# ---------------------------------------------------------------------------

def list_flows() -> None:
    """List all WhatsApp Flows for this WABA."""
    waba_id = _get_waba_id()
    api_url = os.environ.get("WHATSAPP_API_URL", "https://graph.facebook.com/v18.0")

    if waba_id:
        url = f"{api_url}/{waba_id}/flows"
    else:
        # Fall back to phone-number-level listing
        phone_id = _require_env("WHATSAPP_PHONE_NUMBER_ID")
        url = f"{api_url}/{phone_id}/flows"

    print(f"📋 Fetching flows from {url}...")
    response = requests.get(url, headers=_auth_header())

    if response.ok:
        flows = response.json().get("data", [])
        if not flows:
            print("ℹ️  No flows found.")
            return
        print(f"\nFound {len(flows)} flow(s):\n")
        for flow in flows:
            status = flow.get("status", "?")
            status_icon = "✅" if status == "PUBLISHED" else "📝" if status == "DRAFT" else "⚠️"
            print(f"  {status_icon} {flow.get('name', '?')} (ID: {flow.get('id')})")
            print(f"     Status: {status} | Categories: {flow.get('categories', [])}")
            print()
    else:
        print(f"❌ Failed to list flows: HTTP {response.status_code}")
        print(f"   {response.text}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# 4. Create / Upload a Flow
# ---------------------------------------------------------------------------

def create_flow(flow_name: str, flow_file: str, categories: list[str] | None = None) -> str:
    """
    Create a new Flow on Meta and upload its JSON definition.

    Returns the created flow ID.
    """
    waba_id = _get_waba_id()
    api_url = os.environ.get("WHATSAPP_API_URL", "https://graph.facebook.com/v18.0")

    if not waba_id:
        print("❌ WHATSAPP_WABA_ID is required to create a flow. Add it to your .env file.")
        sys.exit(1)

    if not os.path.exists(flow_file):
        print(f"❌ Flow file not found: {flow_file}")
        sys.exit(1)

    # Step 1: Create the flow (get an ID)
    create_url = f"{api_url}/{waba_id}/flows"
    categories = categories or ["OTHER"]

    print(f"📝 Creating flow '{flow_name}' on Meta...")
    create_resp = requests.post(
        create_url,
        headers={**_auth_header(), "Content-Type": "application/json"},
        json={"name": flow_name, "categories": categories},
    )

    if not create_resp.ok:
        print(f"❌ Failed to create flow: HTTP {create_resp.status_code}")
        print(f"   {create_resp.text}")
        sys.exit(1)

    flow_id = create_resp.json().get("id")
    print(f"✅ Flow created with ID: {flow_id}")

    # Step 2: Upload the Flow JSON
    _upload_flow_json(flow_id, flow_file, api_url)

    print()
    print("─" * 60)
    print(f"Flow ID: {flow_id}")
    print()
    print("Add this to your .env:")
    if "bundle" in flow_name.lower() or "data" in flow_name.lower():
        print(f"  WHATSAPP_BUY_BUNDLE_FLOW_ID={flow_id}")
    elif "deposit" in flow_name.lower():
        print(f"  WHATSAPP_DEPOSIT_FLOW_ID={flow_id}")
    else:
        print(f"  WHATSAPP_<YOUR_FLOW>_FLOW_ID={flow_id}")
    print()
    print("Then publish the flow when ready:")
    print(f"  python scripts/manage_flows.py --publish-flow --flow-id {flow_id}")
    print("─" * 60)

    return flow_id


def _upload_flow_json(flow_id: str, flow_file: str, api_url: str) -> None:
    """Upload (or replace) the Flow JSON definition for an existing flow."""
    upload_url = f"{api_url}/{flow_id}/assets"

    print(f"⬆️  Uploading Flow JSON from {flow_file}...")

    with open(flow_file, "rb") as f:
        response = requests.post(
            upload_url,
            headers=_auth_header(),
            files={"file": ("flow.json", f, "application/json")},
            data={"name": "flow.json", "asset_type": "FLOW_JSON"},
        )

    if response.ok:
        result = response.json()
        validation_errors = result.get("validation_errors", [])
        if validation_errors:
            print(f"⚠️  Flow JSON uploaded with validation errors:")
            for err in validation_errors:
                print(f"   - {err}")
        else:
            print(f"✅ Flow JSON uploaded successfully!")
    else:
        print(f"❌ Failed to upload Flow JSON: HTTP {response.status_code}")
        print(f"   {response.text}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# 5. Update Flow JSON
# ---------------------------------------------------------------------------

def update_flow(flow_id: str, flow_file: str) -> None:
    """Re-upload the Flow JSON for an existing flow (e.g., after edits)."""
    api_url = os.environ.get("WHATSAPP_API_URL", "https://graph.facebook.com/v18.0")
    _upload_flow_json(flow_id, flow_file, api_url)


# ---------------------------------------------------------------------------
# 6. Get Flow Details
# ---------------------------------------------------------------------------

def get_flow(flow_id: str) -> None:
    """Fetch and print details of a specific flow."""
    api_url = os.environ.get("WHATSAPP_API_URL", "https://graph.facebook.com/v18.0")
    url = f"{api_url}/{flow_id}?fields=id,name,status,categories,validation_errors,endpoint_uri"

    print(f"🔍 Fetching flow {flow_id}...")
    response = requests.get(url, headers=_auth_header())

    if response.ok:
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"❌ Failed to get flow: HTTP {response.status_code}")
        print(f"   {response.text}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# 7. Publish Flow (Manual step — required before users can trigger it)
# ---------------------------------------------------------------------------

def publish_flow(flow_id: str) -> None:
    """
    Publish a flow — makes it available for users to interact with.

    IMPORTANT: Once published, a flow cannot be edited. To make changes,
    you must create a new flow (it will be a new draft version).
    """
    api_url = os.environ.get("WHATSAPP_API_URL", "https://graph.facebook.com/v18.0")
    url = f"{api_url}/{flow_id}/publish"

    print(f"🚀 Publishing flow {flow_id}...")
    print("   ⚠️  Published flows cannot be edited. Create a new flow for future changes.")
    print()

    confirm = input("   Type 'yes' to confirm: ").strip().lower()
    if confirm != "yes":
        print("   Aborted.")
        return

    response = requests.post(url, headers=_auth_header())

    if response.ok:
        print(f"✅ Flow {flow_id} published successfully!")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"❌ Failed to publish flow: HTTP {response.status_code}")
        print(f"   {response.text}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# 8. Delete Flow
# ---------------------------------------------------------------------------

def delete_flow(flow_id: str) -> None:
    """Delete a flow (only works if it's in DRAFT status)."""
    api_url = os.environ.get("WHATSAPP_API_URL", "https://graph.facebook.com/v18.0")
    url = f"{api_url}/{flow_id}"

    print(f"🗑️  Deleting flow {flow_id}...")
    confirm = input("   This is irreversible. Type 'yes' to confirm: ").strip().lower()
    if confirm != "yes":
        print("   Aborted.")
        return

    response = requests.delete(url, headers=_auth_header())

    if response.ok:
        print(f"✅ Flow {flow_id} deleted.")
    else:
        print(f"❌ Failed to delete flow: HTTP {response.status_code}")
        print(f"   {response.text}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# 9. Set Endpoint URI on a Flow
# ---------------------------------------------------------------------------

def set_endpoint(flow_id: str, endpoint_uri: str) -> None:
    """Set the data exchange endpoint URI for a flow."""
    api_url = os.environ.get("WHATSAPP_API_URL", "https://graph.facebook.com/v18.0")
    url = f"{api_url}/{flow_id}"

    print(f"🔗 Setting endpoint URI for flow {flow_id}: {endpoint_uri}")
    response = requests.post(
        url,
        headers={**_auth_header(), "Content-Type": "application/json"},
        json={"endpoint_uri": endpoint_uri},
    )

    if response.ok:
        print(f"✅ Endpoint URI set successfully!")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"❌ Failed to set endpoint: HTTP {response.status_code}")
        print(f"   {response.text}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Manage WhatsApp Flows lifecycle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          # Generate RSA key pair (do this once)
          python scripts/manage_flows.py --generate-keys

          # Upload public key to Meta (do this once, or after rotating keys)
          python scripts/manage_flows.py --upload-key

          # Upload public key from a specific file
          python scripts/manage_flows.py --upload-key --key-file flows_public_key.pem

          # List all flows
          python scripts/manage_flows.py --list-flows

          # Create the Buy Bundle flow
          python scripts/manage_flows.py --create-flow \\
              --flow-name "Buy Data Bundle" \\
              --flow-file whatsapp/flows/buy_bundle_flow.json

          # Create the Deposit flow
          python scripts/manage_flows.py --create-flow \\
              --flow-name "Deposit Funds" \\
              --flow-file whatsapp/flows/deposit_flow.json

          # Set the data exchange endpoint URI (required for server-driven flows)
          python scripts/manage_flows.py --set-endpoint \\
              --flow-id 1234567890 \\
              --endpoint-uri https://api.yourdomain.com/api/v1/webhooks/whatsapp/flow

          # Check flow status / validation errors
          python scripts/manage_flows.py --get-flow --flow-id 1234567890

          # Publish the flow (makes it live — irreversible!)
          python scripts/manage_flows.py --publish-flow --flow-id 1234567890

          # Update flow JSON without republishing (only works on DRAFT flows)
          python scripts/manage_flows.py --update-flow \\
              --flow-id 1234567890 \\
              --flow-file whatsapp/flows/buy_bundle_flow.json
        """),
    )

    parser.add_argument("--generate-keys", action="store_true",
                        help="Generate a new RSA 2048-bit key pair")
    parser.add_argument("--keys-dir", default=".",
                        help="Directory to save generated keys (default: current dir)")

    parser.add_argument("--upload-key", action="store_true",
                        help="Upload RSA public key to Meta")
    parser.add_argument("--key-file", default=None,
                        help="Path to public key PEM file (optional if private key is in .env)")

    parser.add_argument("--list-flows", action="store_true",
                        help="List all WhatsApp Flows")

    parser.add_argument("--create-flow", action="store_true",
                        help="Create a new flow and upload its JSON")
    parser.add_argument("--flow-name", default=None,
                        help="Flow name for --create-flow")
    parser.add_argument("--flow-file", default=None,
                        help="Path to Flow JSON file")
    parser.add_argument("--categories", nargs="+", default=["OTHER"],
                        help="Flow categories (default: OTHER)")

    parser.add_argument("--update-flow", action="store_true",
                        help="Re-upload Flow JSON for an existing DRAFT flow")
    parser.add_argument("--flow-id", default=None,
                        help="Flow ID for operations that require it")

    parser.add_argument("--get-flow", action="store_true",
                        help="Get details of a specific flow")

    parser.add_argument("--publish-flow", action="store_true",
                        help="Publish a flow (makes it live — irreversible!)")

    parser.add_argument("--delete-flow", action="store_true",
                        help="Delete a DRAFT flow")

    parser.add_argument("--set-endpoint", action="store_true",
                        help="Set the data exchange endpoint URI for a flow")
    parser.add_argument("--endpoint-uri", default=None,
                        help="HTTPS endpoint URI for data exchange")

    args = parser.parse_args()

    if args.generate_keys:
        generate_keys(output_dir=args.keys_dir)

    elif args.upload_key:
        upload_public_key(key_file=args.key_file)

    elif args.list_flows:
        list_flows()

    elif args.create_flow:
        if not args.flow_name:
            parser.error("--create-flow requires --flow-name")
        if not args.flow_file:
            parser.error("--create-flow requires --flow-file")
        create_flow(args.flow_name, args.flow_file, args.categories)

    elif args.update_flow:
        if not args.flow_id:
            parser.error("--update-flow requires --flow-id")
        if not args.flow_file:
            parser.error("--update-flow requires --flow-file")
        update_flow(args.flow_id, args.flow_file)

    elif args.get_flow:
        if not args.flow_id:
            parser.error("--get-flow requires --flow-id")
        get_flow(args.flow_id)

    elif args.publish_flow:
        if not args.flow_id:
            parser.error("--publish-flow requires --flow-id")
        publish_flow(args.flow_id)

    elif args.delete_flow:
        if not args.flow_id:
            parser.error("--delete-flow requires --flow-id")
        delete_flow(args.flow_id)

    elif args.set_endpoint:
        if not args.flow_id:
            parser.error("--set-endpoint requires --flow-id")
        if not args.endpoint_uri:
            parser.error("--set-endpoint requires --endpoint-uri")
        set_endpoint(args.flow_id, args.endpoint_uri)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
