# Security Fixes Migration Guide

## Overview

The security fixes have been applied to protect critical user endpoints with authentication and authorization. This guide will help you deploy these changes to production.

## What Changed

### 1. New Authentication System

- All user-specific endpoints now require authentication headers
- HMAC signature verification ensures requests come from legitimate bots
- Users can only access their own data (authorization enforced)

### 2. Admin Security Improved

- Dedicated `ADMIN_API_KEYS` replace usage of `SUPABASE_KEY`
- Admin endpoints have stricter rate limiting
- Audit logging for admin actions

### 3. Response DTOs Added

- Type-safe response models for consistency
- Better API documentation
- Prevents accidental data exposure

## Breaking Changes

### Bot Integration Required

Your Telegram and WhatsApp bots **MUST** now send these headers with every API request:

```python
headers = {
    "X-User-ID": user_id,          # telegram_id or phone number
    "X-Platform": "telegram",       # or "whatsapp"
    "X-Signature": hmac_signature   # HMAC-SHA256 signature
}
```

### Generating the Signature

The signature must be generated as follows:

```python
import hmac
import hashlib

# Your bot's code
def generate_signature(user_id: str, platform: str, secret: str) -> str:
    """
    Generate HMAC signature for API request.

    Args:
        user_id: telegram_id or phone number
        platform: "telegram" or "whatsapp"
        secret: BOT_BACKEND_SECRET from .env

    Returns:
        Hex-encoded HMAC-SHA256 signature
    """
    message = f"{user_id}:{platform}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature

# Example usage
user_id = "123456789"
platform = "telegram"
secret = os.getenv("BOT_BACKEND_SECRET")

signature = generate_signature(user_id, platform, secret)

# Make API request
response = requests.get(
    "https://your-backend.com/api/v1/wallet/balance/123456789",
    headers={
        "X-User-ID": user_id,
        "X-Platform": platform,
        "X-Signature": signature
    }
)
```

## Deployment Steps

### Step 1: Generate Secrets

```bash
# Generate BOT_BACKEND_SECRET
openssl rand -hex 32

# Generate ADMIN_API_KEYS (generate 2-3 keys)
openssl rand -hex 32
openssl rand -hex 32
```

### Step 2: Update Backend .env

Add to your backend's `.env` file:

```bash
# Copy output from command above
BOT_BACKEND_SECRET=<your_generated_secret>

# Comma-separated admin keys
ADMIN_API_KEYS=<key1>,<key2>
```

### Step 3: Update Bot .env

Add the **SAME** secret to your bot's `.env` file:

```bash
# Must be IDENTICAL to backend BOT_BACKEND_SECRET
BOT_BACKEND_SECRET=<same_secret_as_backend>

# Backend API URL
BACKEND_API_URL=https://your-backend.com
```

### Step 4: Update Bot Code

Update your bot's API client to send authentication headers:

#### Telegram Bot Example

```python
# bot/utils/backend_client.py (or create this file)

import os
import hmac
import hashlib
import httpx

class BackendAPI:
    def __init__(self):
        self.base_url = os.getenv("BACKEND_API_URL")
        self.secret = os.getenv("BOT_BACKEND_SECRET")

    def _generate_signature(self, user_id: str, platform: str) -> str:
        """Generate HMAC signature for authentication."""
        message = f"{user_id}:{platform}"
        return hmac.new(
            self.secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

    def _get_headers(self, user_id: str, platform: str = "telegram") -> dict:
        """Get authentication headers for API request."""
        return {
            "X-User-ID": str(user_id),
            "X-Platform": platform,
            "X-Signature": self._generate_signature(str(user_id), platform)
        }

    async def get_balance(self, telegram_id: int):
        """Get user's wallet balance."""
        headers = self._get_headers(str(telegram_id), "telegram")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/wallet/balance/{telegram_id}",
                headers=headers,
                params={"identifier_type": "telegram_id"}
            )
            response.raise_for_status()
            return response.json()

    async def get_history(self, telegram_id: int, limit: int = 10):
        """Get user's transaction history."""
        headers = self._get_headers(str(telegram_id), "telegram")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/users/{telegram_id}/history",
                headers=headers,
                params={"identifier_type": "telegram_id", "limit": limit}
            )
            response.raise_for_status()
            return response.json()

    async def create_order(self, telegram_id: int, bundle_id: str, phone: str):
        """Create a bundle purchase order."""
        headers = self._get_headers(str(telegram_id), "telegram")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/orders",
                headers=headers,
                json={
                    "telegram_id": str(telegram_id),
                    "bundle_id": bundle_id,
                    "phone": phone
                }
            )
            response.raise_for_status()
            return response.json()

# Use in your handlers
api = BackendAPI()

# In your handler
async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        data = await api.get_balance(user_id)
        await update.message.reply_text(
            f"💰 Your Balance: GHS {data['balance']}"
        )
    except httpx.HTTPError as e:
        await update.message.reply_text("Error fetching balance. Please try again.")
```

#### WhatsApp Bot Example

```python
# whatsapp/utils/backend_client.py

import os
import hmac
import hashlib
import httpx

class WhatsAppBackendAPI:
    def __init__(self):
        self.base_url = os.getenv("BACKEND_API_URL")
        self.secret = os.getenv("BOT_BACKEND_SECRET")

    def _generate_signature(self, phone: str) -> str:
        """Generate HMAC signature for WhatsApp user."""
        message = f"{phone}:whatsapp"
        return hmac.new(
            self.secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

    def _get_headers(self, phone: str) -> dict:
        """Get authentication headers for WhatsApp user."""
        return {
            "X-User-ID": phone,
            "X-Platform": "whatsapp",
            "X-Signature": self._generate_signature(phone)
        }

    async def get_balance(self, phone: str):
        """Get user's wallet balance."""
        headers = self._get_headers(phone)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/wallet/balance/{phone}",
                headers=headers,
                params={"identifier_type": "phone"}
            )
            response.raise_for_status()
            return response.json()
```

### Step 5: Deploy Backend

```bash
# Pull latest code
cd /path/to/databot
git pull origin main

# Restart backend
docker-compose restart backend
# OR
sudo systemctl restart databot

# Check logs
docker-compose logs -f backend
```

### Step 6: Deploy Bot Updates

```bash
# Pull latest bot code
cd /path/to/bot
git pull origin main

# Update .env with BOT_BACKEND_SECRET

# Restart bot
docker-compose restart telegram-bot
# OR
sudo systemctl restart telegram-bot
```

### Step 7: Test

```bash
# Test balance endpoint
curl -X GET "https://your-backend.com/api/v1/wallet/balance/123456789?identifier_type=telegram_id" \
  -H "X-User-ID: 123456789" \
  -H "X-Platform: telegram" \
  -H "X-Signature: <generated_signature>"

# Test admin endpoint
curl -X GET "https://your-backend.com/api/v1/users/123456789/debug-full?identifier_type=telegram_id" \
  -H "X-API-Key: <your_admin_key>"
```

## Affected Endpoints

### Now Require Authentication

All these endpoints now require `X-User-ID`, `X-Platform`, and `X-Signature` headers:

- `POST /api/v1/users/ensure`
- `POST /api/v1/users/ensure-whatsapp`
- `GET /api/v1/users/{identifier}/history`
- `GET /api/v1/wallet/balance/{identifier}`
- `POST /api/v1/wallet/deposit/init`
- `GET /api/v1/referrals/code/{identifier}`
- `GET /api/v1/referrals/referrals/{identifier}`

### Admin Endpoints

These require `X-API-Key` header with a valid admin key:

- `GET /api/v1/users/{identifier}/debug-full`
- Any future admin endpoints

### Unchanged (No Auth Required)

These endpoints remain public:

- `GET /api/v1/bundles` (listing bundles)
- `POST /api/v1/webhooks/paystack` (webhook)
- `POST /api/v1/webhooks/telegram` (webhook)
- `POST /api/v1/webhooks/whatsapp` (webhook)

## Troubleshooting

### "Invalid request signature" Error

**Cause:** The HMAC signature doesn't match.

**Solutions:**

1. Ensure `BOT_BACKEND_SECRET` is **identical** in bot and backend `.env`
2. Verify signature generation matches the format: `user_id:platform`
3. Check that user_id doesn't have extra whitespace
4. Ensure using SHA256 hash algorithm

```python
# Debug signature generation
user_id = "123456789"
platform = "telegram"
secret = "your_secret"

message = f"{user_id}:{platform}"
print(f"Message: {message}")

signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
print(f"Signature: {signature}")
```

### "Cannot access other users' data" Error

**Cause:** The identifier in the URL doesn't match the authenticated user.

**Solution:**
Ensure `X-User-ID` header matches the `{identifier}` in the URL path.

```python
# ✅ Correct
headers = {"X-User-ID": "123456789", ...}
url = "/api/v1/wallet/balance/123456789"

# ❌ Wrong - mismatch
headers = {"X-User-ID": "123456789", ...}
url = "/api/v1/wallet/balance/987654321"  # Different user!
```

### "Invalid admin API key" Error

**Cause:** The `X-API-Key` header is not in `ADMIN_API_KEYS`.

**Solution:**

1. Check that `ADMIN_API_KEYS` is set in backend `.env`
2. Verify the key is in the comma-separated list
3. No spaces around the keys in the list

```bash
# ✅ Correct
ADMIN_API_KEYS=key1,key2,key3

# ❌ Wrong (spaces)
ADMIN_API_KEYS=key1, key2, key3
```

## Rollback Plan

If you need to roll back:

```bash
# 1. Checkout previous commit
git checkout <previous_commit_hash>

# 2. Restart services
docker-compose restart

# 3. Bots will continue working without auth headers
# (old code doesn't require them)
```

## Security Notes

1. **Never commit secrets to git** - Use `.env` files and `.gitignore`
2. **Rotate keys periodically** - Generate new `BOT_BACKEND_SECRET` every 6 months
3. **Monitor audit logs** - Check for suspicious admin access
4. **Use HTTPS** - Always use HTTPS in production for API calls

## Support

If you encounter issues:

1. Check logs: `docker-compose logs -f backend`
2. Verify environment variables are loaded
3. Test signature generation manually
4. Review the security review document for details

---

**Migration Date:** 2025-12-30  
**Version:** 2.0.0 (Security Update)
