# Security Fixes - Quick Reference

## 🎯 What Was Fixed

### Critical Issues (Fixed ✅)

1. **User History Endpoint** - Now requires authentication, users can only view own history
2. **Balance Endpoint** - Protected with user verification
3. **Admin Authentication** - Uses dedicated ADMIN_API_KEYS instead of SUPABASE_KEY

### Medium Priority (Fixed ✅)

4. **Referral Endpoints** - Authentication required
5. **Response DTOs** - Type-safe responses added
6. **Rate Limiting** - Applied to all sensitive endpoints

---

## 📦 What You Need to Do

### 1. Generate Secrets

```bash
# Generate BOT_BACKEND_SECRET
openssl rand -hex 32

# Generate 2 admin keys
openssl rand -hex 32
openssl rand -hex 32
```

### 2. Update Backend .env

```bash
# Add these lines to .env
BOT_BACKEND_SECRET=<your_generated_secret>
ADMIN_API_KEYS=<key1>,<key2>
```

### 3. Update Bot .env

```bash
# Add this to bot's .env (MUST be same as backend)
BOT_BACKEND_SECRET=<same_secret_as_backend>
```

### 4. Update Bot Code

Your bots must now send these headers with every API request:

```python
import hmac
import hashlib

def generate_signature(user_id: str, platform: str, secret: str) -> str:
    message = f"{user_id}:{platform}"
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

# Example request
headers = {
    "X-User-ID": "123456789",
    "X-Platform": "telegram",  # or "whatsapp"
    "X-Signature": generate_signature("123456789", "telegram", SECRET)
}

response = requests.get(
    "https://your-backend.com/api/v1/wallet/balance/123456789",
    headers=headers
)
```

**See `.agent/bot_api_client_example.py` for complete implementation!**

---

## 📋 Affected Endpoints

### Now Require Auth Headers

- `POST /api/v1/users/ensure`
- `POST /api/v1/users/ensure-whatsapp`
- `GET /api/v1/users/{id}/history`
- `GET /api/v1/wallet/balance/{id}`
- `POST /api/v1/wallet/deposit/init`
- `GET /api/v1/referrals/code/{id}`
- `GET /api/v1/referrals/referrals/{id}`

### Admin Endpoints (Need Admin Key)

- `GET /api/v1/users/{id}/debug-full`

### Unchanged (Public)

- `GET /api/v1/bundles`
- All webhook endpoints

---

## 🚀 Quick Deploy

```bash
# 1. Update .env files (backend and bot)
# 2. Deploy backend
cd /path/to/databot
git pull
docker-compose restart backend

# 3. Update bot code with auth headers
# 4. Deploy bot
cd /path/to/bot
git pull
docker-compose restart telegram-bot
```

---

## 📚 Full Documentation

- **Complete Walkthrough:** `walkthrough.md` (in artifacts)
- **Migration Guide:** `.agent/MIGRATION_GUIDE.md`
- **Bot Client Example:** `.agent/bot_api_client_example.py`
- **Security Review:** `.agent/SECURITY_REVIEW.md`

---

## ⚠️ Important Notes

1. **BOT_BACKEND_SECRET must be identical** in bot and backend .env
2. **Bots will not work** until you add auth headers to their code
3. **Test locally first** before deploying to production
4. **Never commit secrets to git** - use .env files

---

## 🆘 Troubleshooting

### "Invalid request signature"

→ Check that BOT_BACKEND_SECRET matches in both .env files

### "Cannot access other users' data"

→ X-User-ID header must match the identifier in URL path

### "Invalid admin API key"

→ Ensure ADMIN_API_KEYS is set in backend .env

**See Migration Guide for detailed troubleshooting!**

---

**Status:** ✅ Implementation Complete - Ready for Bot Integration  
**Next Step:** Update bot code to send auth headers using the example client
