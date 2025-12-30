# Databot Security Review

## Focus: Mass Assignment, DTOs, and Server-Side Authorization

**Review Date:** 2025-12-30  
**Reviewer:** Antigravity AI  
**Project:** Databot - Data Bundle Purchase System

---

## Executive Summary

This review assesses the databot codebase for three critical software engineering patterns:

1. **Mass Assignment Vulnerabilities** - Can users inject unauthorized fields?
2. **Data Transfer Objects (DTOs)** - Are request/response schemas properly defined?
3. **Server-Side Authorization** - Is every endpoint protected appropriately?

### Overall Security Score: **7/10** ⚠️

**Strengths:**

- ✅ Good use of Pydantic models for validation
- ✅ Proper repository pattern separating data access
- ✅ Idempotent wallet operations prevent double-crediting
- ✅ Webhook signature verification implemented

**Critical Issues:**

- 🔴 **NO DTO** for user updates - mass assignment vulnerability
- 🔴 **Missing or weak authorization** on several endpoints
- 🔴 **Admin endpoints** inadequately protected
- 🟡 Query parameter mass assignment in some endpoints

---

## 1. Mass Assignment Analysis

### 🔴 CRITICAL: No DTOs for User Updates

Currently, your codebase **doesn't expose user update endpoints**, which is good. However, if you ever add them, you need DTOs.

**Risk:** If you implement user updates without DTOs, users could set:

- `balance` → self-credit money
- `referral_code` → steal referral codes
- `referred_by` → falsify referral relationships
- Database metadata fields (`id`, `created_at`, etc.)

**Recommendation:**

```python
# DO NOT IMPLEMENT WITHOUT DTO
# ❌ DANGEROUS - Never do this:
@router.patch("/users/{user_id}")
async def update_user(user_id: str, user_data: dict):
    # Users can inject ANY field
    await user_repo.update(user_id, user_data)

# ✅ SAFE - Use DTO:
class UserUpdateDTO(BaseModel):
    name: Optional[str] = None
    # Only allow specific, safe fields

@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    updates: UserUpdateDTO,
    current_user: str = Depends(get_current_user)
):
    # Authorization: can only update own profile
    if current_user != user_id:
        raise HTTPException(403, "Cannot update other users")

    await user_repo.update(user_id, updates.dict(exclude_unset=True))
```

### ✅ GOOD: Query Parameters with Defaults

Your endpoints use explicit parameters, which is safe:

**File:** `app/api/v1/users.py:30-35`

```python
@router.post("/ensure")
async def ensure_user(
    telegram_id: str,
    name: str = None,
    referral_code: str = None,
):
```

✅ **Safe:** Only `telegram_id`, `name`, and `referral_code` can be provided.  
✅ **Cannot** inject: `balance`, `is_admin`, etc.

### ✅ GOOD: Pydantic DTOs for Structured Inputs

**File:** `app/api/v1/wallet.py:19-24`

```python
class DepositInitRequest(BaseModel):
    telegram_id: Optional[str] = None
    user_id: Optional[str] = None
    amount: Decimal
    phone: str
    provider: str
```

✅ **Safe:** Pydantic validates types and only accepts defined fields.

### ✅ GOOD: Order Creation DTO

**File:** `app/api/v1/orders.py:11-16`

```python
class CreateOrderRequest(BaseModel):
    telegram_id: Optional[str] = None
    user_id: Optional[str] = None
    bundle_id: str
    phone: str
```

✅ **Safe:** Users cannot inject `price`, `status`, or other order metadata.

---

## 2. Data Transfer Objects (DTOs) Inventory

### Existing DTOs ✅

| DTO Name                | File                     | Purpose                | Status  |
| ----------------------- | ------------------------ | ---------------------- | ------- |
| `WhatsAppUserRequest`   | `api/v1/users.py:25-28`  | WhatsApp user creation | ✅ Good |
| `DepositInitRequest`    | `api/v1/wallet.py:19-24` | Deposit initialization | ✅ Good |
| `DepositConfirmRequest` | `api/v1/wallet.py:27-29` | OTP submission         | ✅ Good |
| `CreateOrderRequest`    | `api/v1/orders.py:11-15` | Bundle purchase        | ✅ Good |

### Missing DTOs 🟡

| Missing DTO         | Where Needed               | Risk Level                  |
| ------------------- | -------------------------- | --------------------------- |
| `UserUpdateDTO`     | User profile updates       | 🔴 High (if endpoint added) |
| `WalletResponseDTO` | `/wallet/balance` response | 🟡 Medium (consistency)     |
| `OrderResponseDTO`  | `/orders` response         | 🟡 Medium (consistency)     |
| `BundleResponseDTO` | `/bundles` response        | 🟢 Low (read-only)          |

### Recommendations

#### Add Response DTOs for Consistency

**Current (Inline Dict):**

```python
# app/api/v1/wallet.py:133-139
return {
    "user_id": user["id"],
    "telegram_id": user.get("telegram_id"),
    "phone": user.get("whatsapp_phone"),
    "balance": str(balance),
    "currency": "GHS"
}
```

**Recommended (DTO):**

```python
class BalanceResponseDTO(BaseModel):
    user_id: str
    telegram_id: Optional[str]
    phone: Optional[str]
    balance: str
    currency: str = "GHS"

@router.get("/balance/{identifier}", response_model=BalanceResponseDTO)
async def get_balance(...):
    # FastAPI auto-validates response
    return BalanceResponseDTO(
        user_id=user["id"],
        telegram_id=user.get("telegram_id"),
        phone=user.get("whatsapp_phone"),
        balance=str(balance)
    )
```

**Benefits:**

- ✅ Auto-validation of responses
- ✅ OpenAPI docs show exact response shape
- ✅ Prevents accidental exposure of internal fields
- ✅ Type safety for clients

---

## 3. Server-Side Authorization Analysis

### 🔴 CRITICAL ISSUES

#### Issue 1: No Authentication on User History Endpoint

**File:** `app/api/v1/users.py:92-171`

```python
@router.get("/{identifier}/history")
async def get_user_history(
    identifier: str,
    limit: int = Query(10, ge=1, le=100),
    identifier_type: str = Query("telegram_id", regex="^(telegram_id|phone)$")
):
```

**Vulnerability:** 🔴 **ANYONE can view ANY user's history** by guessing their telegram_id or phone number.

**Example Attack:**

```bash
# Attacker can enumerate users
curl "https://api.example.com/api/v1/users/123456789/history?identifier_type=telegram_id"
curl "https://api.example.com/api/v1/users/233123456789/history?identifier_type=phone"
```

**Impact:**

- 🔴 Privacy violation - view other users' transactions
- 🔴 Financial data exposure - see deposit amounts, bundle purchases
- 🔴 GDPR/data protection violation

**Fix Required:**

```python
# Add authentication dependency
async def get_current_user_identifier(
    x_user_id: str = Header(..., alias="X-User-ID"),
    x_platform: str = Header(..., alias="X-Platform")
) -> Tuple[str, str]:
    """Verify user identity from authenticated bot request."""
    # In production, verify this comes from your bot backend
    # For now, trust the headers from bot
    return (x_user_id, x_platform)

@router.get("/{identifier}/history")
async def get_user_history(
    identifier: str,
    limit: int = Query(10, ge=1, le=100),
    identifier_type: str = Query("telegram_id", regex="^(telegram_id|phone)$"),
    current_user: Tuple[str, str] = Depends(get_current_user_identifier)
):
    current_identifier, current_platform = current_user

    # AUTHORIZATION: Can only view own history
    if identifier != current_identifier:
        raise HTTPException(status_code=403, detail="Cannot view other users' history")

    # ... rest of code
```

#### Issue 2: Weak Admin Authentication

**File:** `app/api/v1/users.py:15-22`

```python
async def verify_admin_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != settings.SUPABASE_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True
```

**Issues:**

- 🟡 Uses `SUPABASE_KEY` as admin key - **Supabase key is NOT meant for this**
- 🟡 No rate limiting on admin endpoints
- 🟡 Single shared key for all admins (no audit trail)

**Recommendation:**

```python
# Create dedicated admin keys
ADMIN_API_KEYS = settings.ADMIN_API_KEYS.split(",")  # Store in .env

async def verify_admin_api_key(x_api_key: str = Header(...)):
    if x_api_key not in ADMIN_API_KEYS:
        # Log failed attempt
        logger.warning(f"Failed admin auth attempt with key: {x_api_key[:8]}...")
        raise HTTPException(status_code=403, detail="Invalid admin API key")
    return x_api_key  # Return key to identify which admin

# Add rate limiting
@router.get("/{identifier}/debug-full")
@limiter.limit("10/hour")  # Strict limit for debug endpoints
async def debug_full_user_data(
    identifier: str,
    admin_key: str = Depends(verify_admin_api_key)
):
    logger.info(f"Admin debug access by key: {admin_key[:8]}... for user: {identifier}")
    # ... rest of code
```

#### Issue 3: Balance Endpoint Has No Authorization

**File:** `app/api/v1/wallet.py:108-139`

```python
@router.get("/balance/{identifier}")
async def get_balance(
    identifier: str,
    identifier_type: str = "telegram_id"
):
```

**Vulnerability:** 🔴 **Anyone can check anyone's balance**

**Fix:** Same as history endpoint - require authentication and authorization.

#### Issue 4: Referral Endpoints Unprotected

**File:** `app/api/v1/referrals.py`

Both endpoints (`/code/{identifier}` and `/referrals/{identifier}`) have no authorization.

**Risk:** 🟡 Medium - Attackers can enumerate referral relationships and codes.

### ✅ GOOD: Protected Endpoints

#### Webhook Signature Verification ✅

**File:** `app/api/v1/webhooks/paystack.py:34`

```python
if not paystack_service.verify_webhook_signature(body, signature_header):
    raise HTTPException(status_code=401, detail="Invalid signature")
```

✅ **Good:** Webhooks verify cryptographic signatures.

#### Idempotent Wallet Operations ✅

**File:** `app/services/wallet_service.py:54-75`

```python
# IDEMPOTENCY CHECK: If transaction is already SUCCESS, don't credit again
if transaction["status"] == TransactionStatus.SUCCESS.value:
    raw_payload = transaction.get("raw_payload") or {}
    if isinstance(raw_payload, dict) and raw_payload.get("wallet_credited"):
        logger.info(f"Transaction {reference} already processed...")
        return wallet
```

✅ **Excellent:** Prevents double-crediting if webhook fires multiple times.

---

## 4. Additional Security Findings

### 🟡 MEDIUM: Order Service Can Be Exploited

**File:** `app/services/order_service.py` (not fully reviewed, but inferred)

**Potential Issue:** Need to verify:

1. Can users specify `price` when creating orders?
2. Is bundle price validated against database?
3. What prevents users from creating orders with `price=0.01`?

**Verification Needed:**

```python
# Ensure order service does this:
bundle = await bundle_repo.get_by_id(bundle_id)
if request.price != bundle.price:  # If user can send price
    raise ValueError("Price mismatch with bundle")
```

### ✅ GOOD: No Direct Database Access in Endpoints

All endpoints use services/repositories - no raw SQL in API layer.

### 🟡 MEDIUM: CORS Configuration

**File:** `app/main.py:134-142`

```python
allowed_origins = settings.ALLOWED_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Check:** Ensure `ALLOWED_ORIGINS` is properly restricted in production:

```bash
# .env - Production
ALLOWED_ORIGINS=https://yourdomain.com

# ❌ Don't use in production:
ALLOWED_ORIGINS=*
```

---

## 5. Priority Fixes

### 🔴 HIGH PRIORITY (Fix Immediately)

| #   | Issue                        | File                   | Severity    | Fix                                |
| --- | ---------------------------- | ---------------------- | ----------- | ---------------------------------- |
| 1   | **User history exposed**     | `api/v1/users.py:92`   | 🔴 Critical | Add authentication + authorization |
| 2   | **Balance endpoint exposed** | `api/v1/wallet.py:108` | 🔴 Critical | Add authentication + authorization |
| 3   | **Admin key misuse**         | `api/v1/users.py:20`   | 🟡 High     | Use dedicated admin keys           |

### 🟡 MEDIUM PRIORITY (Fix Soon)

| #   | Issue                            | Severity  | Fix                            |
| --- | -------------------------------- | --------- | ------------------------------ |
| 4   | Referral endpoints unprotected   | 🟡 Medium | Add user verification          |
| 5   | No response DTOs                 | 🟡 Medium | Add structured response models |
| 6   | Admin endpoints not rate-limited | 🟡 Medium | Add strict rate limits         |

### 🟢 LOW PRIORITY (Nice to Have)

| #   | Issue                        | Fix                                         |
| --- | ---------------------------- | ------------------------------------------- |
| 7   | No request logging for audit | Add request logging middleware              |
| 8   | No IP-based rate limiting    | Consider using IP + user_id for rate limits |

---

## 6. Recommended Security Enhancements

### Authentication Strategy

Since you're using Telegram and WhatsApp bots, implement bot-to-backend authentication:

```python
# app/core/auth.py
import hmac
import hashlib
from fastapi import Header, HTTPException

async def verify_bot_request(
    x_user_id: str = Header(...),
    x_platform: str = Header(..., regex="^(telegram|whatsapp)$"),
    x_signature: str = Header(...)
):
    """
    Verify request comes from legitimate bot backend.
    Bot should sign requests with: HMAC-SHA256(user_id + platform, secret)
    """
    secret = settings.BOT_BACKEND_SECRET
    expected_signature = hmac.new(
        secret.encode(),
        f"{x_user_id}:{x_platform}".encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(x_signature, expected_signature):
        raise HTTPException(401, "Invalid request signature")

    return {"user_id": x_user_id, "platform": x_platform}
```

### Apply to All User Endpoints

```python
@router.get("/{identifier}/history")
async def get_user_history(
    identifier: str,
    auth: dict = Depends(verify_bot_request)
):
    # Authorization check
    if identifier != auth["user_id"]:
        raise HTTPException(403, "Cannot access other users' data")
```

### Rate Limiting Strategy

```python
# More granular rate limits
@router.post("/orders")
@limiter.limit("10/minute")  # Prevent abuse
async def create_order(...):

@router.get("/bundles")
@limiter.limit("60/minute")  # Higher for read-only
async def get_bundles(...):
```

---

## 7. Summary of Fixes Needed

### Immediate Actions (This Week)

1. **Add authentication to user-data endpoints:**

   - `/api/v1/users/{identifier}/history`
   - `/api/v1/wallet/balance/{identifier}`
   - `/api/v1/referrals/code/{identifier}`
   - `/api/v1/referrals/referrals/{identifier}`

2. **Fix admin authentication:**

   - Create dedicated `ADMIN_API_KEYS` env variable
   - Stop using `SUPABASE_KEY` for admin auth
   - Add rate limiting to admin endpoints

3. **Add authorization checks:**
   - Users can only view their own data
   - Prevent cross-user data access

### Medium-Term (This Month)

4. **Add response DTOs** for type safety and API documentation
5. **Implement request signing** from bot to backend
6. **Add audit logging** for sensitive operations
7. **Review and test order price validation**

### Long-Term (Nice to Have)

8. Create admin dashboard with proper role-based access
9. Implement JWT-based authentication for future web frontend
10. Add IP-based fraud detection for deposit attempts

---

## 8. Testing Recommendations

### Security Tests to Add

```python
# tests/test_authorization.py

def test_user_cannot_view_other_user_history():
    """Ensure User A cannot view User B's transaction history."""
    response = client.get(
        "/api/v1/users/other_user_telegram_id/history",
        headers={"X-User-ID": "my_telegram_id"}
    )
    assert response.status_code == 403

def test_user_cannot_view_other_user_balance():
    """Ensure User A cannot check User B's wallet balance."""
    response = client.get(
        "/api/v1/wallet/balance/other_user_telegram_id"
    )
    assert response.status_code == 401  # Or 403 after auth added

def test_mass_assignment_protection():
    """Ensure users cannot inject unauthorized fields."""
    response = client.post(
        "/api/v1/users/ensure",
        json={
            "telegram_id": "123456",
            "name": "Test",
            "balance": 999999,  # Should be ignored
            "is_admin": True     # Should be ignored
        }
    )
    user = response.json()
    assert "balance" not in user  # Should not return balance
    # Verify balance wasn't set in database

def test_admin_endpoint_requires_valid_key():
    """Ensure admin endpoints reject invalid API keys."""
    response = client.get(
        "/api/v1/users/123/debug-full",
        headers={"X-API-Key": "invalid_key"}
    )
    assert response.status_code == 403
```

---

## Conclusion

Your databot project has a **solid foundation** with good use of DTOs for inputs and the repository pattern. However, there are **critical authorization gaps** that need immediate attention.

### Risk Summary

- **Data Exposure Risk:** 🔴 **HIGH** - User financial data accessible without authentication
- **Mass Assignment Risk:** 🟢 **LOW** - Good DTO usage for existing endpoints
- **Privilege Escalation Risk:** 🟡 **MEDIUM** - Weak admin authentication

### Next Steps

1. ✅ Review this document with your team
2. 🔴 **Prioritize fixing authorization issues** (user history, balance)
3. 🟡 Implement bot request signing
4. 🟢 Add response DTOs for consistency
5. 📝 Create security testing suite

**Estimated Time to Fix Critical Issues:** 4-6 hours

**Good luck, and let me know if you need help implementing any of these fixes!** 🚀
