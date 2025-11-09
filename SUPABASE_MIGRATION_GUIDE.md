# Supabase REST API Migration Guide

This guide explains the migration from SQLAlchemy/PostgreSQL to Supabase REST API client.

## Overview

The application has been migrated from using SQLAlchemy with direct PostgreSQL connections to using Supabase REST API client. This change was made to avoid connection issues with Supabase's managed PostgreSQL database.

## What Changed

### Architecture Changes

1. **Database Layer**: Replaced SQLAlchemy ORM with Supabase REST API client
2. **Repository Pattern**: Created repository classes for all models (User, Wallet, Transaction, Bundle, Order, Referral)
3. **Service Layer**: Updated all services to use repositories instead of SQLAlchemy sessions
4. **API Endpoints**: Removed `Depends(get_db)` and SQLAlchemy session dependencies

### Key Files Changed

#### New Files
- `app/repository/base.py` - Base repository class
- `app/repository/user_repo.py` - User repository
- `app/repository/wallet_repo.py` - Wallet repository
- `app/repository/transaction_repo.py` - Transaction repository
- `app/repository/bundle_repo.py` - Bundle repository
- `app/repository/order_repo.py` - Order repository
- `app/repository/referral_repo.py` - Referral repository

#### Updated Files
- `app/core/config.py` - Removed `DATABASE_URL`, now requires `SUPABASE_URL` and `SUPABASE_KEY`
- `app/db/supabase_client.py` - Made Supabase client required (no longer optional)
- `app/services/wallet_service.py` - Uses repositories instead of SQLAlchemy
- `app/services/order_service.py` - Uses repositories instead of SQLAlchemy
- `app/services/referral_service.py` - Uses repositories instead of SQLAlchemy
- `app/services/bundle_sync.py` - Uses repositories instead of SQLAlchemy
- `app/services/scheduler.py` - Removed SQLAlchemy session dependency
- All API endpoints in `app/api/v1/` - Removed `Depends(get_db)`
- `app/entrypoint.sh` - Removed database migrations and connection tests

### Removed Dependencies

- SQLAlchemy session management (`get_db` dependency)
- Alembic migrations (migrations now handled via Supabase dashboard)
- Database connection URL configuration
- `SELECT FOR UPDATE` row-level locking (replaced with application-level logic)

## Configuration

### Environment Variables

Update your `.env` file:

```env
# Required: Supabase REST API credentials
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-anon-key-or-service-role-key

# Remove DATABASE_URL - no longer needed
# DATABASE_URL=...
```

### Supabase Setup

1. **Get Supabase Credentials**:
   - Go to your Supabase project dashboard
   - Navigate to Settings → API
   - Copy your `Project URL` (SUPABASE_URL)
   - Copy your `anon` key or `service_role` key (SUPABASE_KEY)

2. **Database Schema**:
   - Create tables in Supabase using SQL Editor or Migration UI
   - Use the same schema as defined in your SQLAlchemy models
   - Ensure all tables have proper indexes and foreign keys

3. **Row Level Security (RLS)**:
   - Configure RLS policies in Supabase if needed
   - For service_role key, RLS is bypassed
   - For anon key, you'll need to set up RLS policies

## Database Schema

The database schema remains the same. You need to create these tables in Supabase:

- `users` - User information
- `wallets` - User wallet balances
- `transactions` - Transaction records
- `bundles` - Data bundle catalog
- `orders` - Purchase orders
- `referrals` - Referral tracking

See your SQLAlchemy models for the exact schema definition.

## Migration Steps

### 1. Create Tables in Supabase

Use the Supabase SQL Editor to create tables. You can generate SQL from your Alembic migrations or create them manually.

### 2. Update Environment Variables

Update your `.env` file with Supabase credentials (see Configuration section).

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

The `supabase` package is already included.

### 4. Test Connection

```bash
python -c "from app.db.supabase_client import supabase; print('Connected!')"
```

### 5. Run Application

```bash
uvicorn app.main:app --reload
```

## Important Considerations

### 1. Atomicity and Concurrency

**Before (SQLAlchemy)**:
- Used `SELECT FOR UPDATE` for row-level locking
- Database transactions ensured atomicity

**After (Supabase REST API)**:
- No built-in row-level locking
- Wallet operations use application-level checks
- For high concurrency, consider:
  - Using Supabase database functions (RPC) for atomic operations
  - Implementing optimistic locking
  - Using a separate locking mechanism (Redis, etc.)

### 2. Transactions

**Before (SQLAlchemy)**:
- Database transactions for multi-step operations
- Rollback on errors

**After (Supabase REST API)**:
- No automatic transactions
- Each operation is independent
- Manual error handling and rollback logic needed

### 3. Query Performance

**Before (SQLAlchemy)**:
- Complex queries with joins
- Efficient database-side filtering

**After (Supabase REST API)**:
- Simple queries via REST API
- Some operations require multiple API calls
- Consider using Supabase database functions for complex queries

### 4. Webhook Transaction Lookup

The webhook handler searches for transactions by Paystack reference. Since Supabase REST API has limited JSON querying, we:
- Search through recent transactions (last 1000)
- Check `raw_payload.data.reference` field
- For better performance, consider adding a `paystack_reference` column

## Testing

### Test Repository Operations

```python
from app.repository.user_repo import UserRepository

user_repo = UserRepository()
user, is_new = user_repo.get_or_create("123456789", "Test User")
print(f"User: {user}, Is New: {is_new}")
```

### Test Service Operations

```python
from app.services.wallet_service import WalletService
from decimal import Decimal

wallet_service = WalletService()
balance = await wallet_service.get_balance("user-id")
print(f"Balance: {balance}")
```

## Troubleshooting

### Connection Issues

**Error**: `Failed to initialize Supabase client`
- Check `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
- Verify credentials in Supabase dashboard
- Ensure network connectivity

### Table Not Found

**Error**: `relation "users" does not exist`
- Create tables in Supabase SQL Editor
- Check table names match your repository expectations
- Verify RLS policies if using anon key

### Permission Issues

**Error**: `permission denied for table`
- Check RLS policies in Supabase
- Use service_role key for admin operations
- Configure RLS policies for anon key

### Performance Issues

- Consider using database functions (RPC) for complex operations
- Add indexes in Supabase for frequently queried fields
- Use connection pooling if available
- Monitor API rate limits

## Future Improvements

1. **Database Functions**: Use Supabase RPC for atomic wallet operations
2. **Caching**: Add Redis for frequently accessed data
3. **Optimistic Locking**: Implement version fields for concurrency control
4. **Batch Operations**: Use Supabase batch API for multiple operations
5. **Real-time Subscriptions**: Use Supabase real-time for live updates

## Rollback Plan

If you need to rollback to SQLAlchemy:

1. Restore `app/core/config.py` with `DATABASE_URL`
2. Restore SQLAlchemy session management
3. Restore all service files to use SQLAlchemy
4. Restore API endpoints with `Depends(get_db)`
5. Run Alembic migrations

## Support

For issues or questions:
- Check Supabase documentation: https://supabase.com/docs
- Review repository code for implementation details
- Check application logs for error messages

