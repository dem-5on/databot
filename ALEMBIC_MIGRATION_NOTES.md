# Alembic Migration Notes

## Important: Alembic No Longer Used

Since we migrated to Supabase REST API, **Alembic is no longer used** for database migrations.

## Why?

- We're using Supabase REST API client, not SQLAlchemy
- Supabase manages the database schema separately
- Migrations are handled through Supabase Dashboard SQL Editor

## What to Do Instead

### 1. Create Tables in Supabase

Go to your Supabase Dashboard → SQL Editor and run SQL to create tables.

Example SQL for creating the `users` table:

```sql
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id TEXT UNIQUE NOT NULL,
    name TEXT,
    phone TEXT,
    provider TEXT,
    referral_code TEXT UNIQUE,
    referred_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code);
CREATE INDEX IF NOT EXISTS idx_users_referred_by ON users(referred_by);
```

### 2. Create All Tables

You need to create these tables:
- `users`
- `wallets`
- `transactions`
- `bundles`
- `orders`
- `referrals`

### 3. Generate SQL from Existing Models

If you want to generate SQL from your SQLAlchemy models, you can:

1. Keep Alembic files for reference (they're still in the repo)
2. Use `alembic upgrade --sql head` to generate SQL (if you temporarily restore DATABASE_URL)
3. Copy the generated SQL to Supabase SQL Editor

### 4. Future Migrations

For future schema changes:
1. Write SQL migration scripts
2. Run them in Supabase SQL Editor
3. Test the changes
4. Document the changes

## Alembic Files Status

The following Alembic files are kept for reference but **not used**:
- `alembic.ini` - Alembic configuration
- `alembic/env.py` - Alembic environment (references removed SQLAlchemy)
- `alembic/versions/` - Migration files (if any)

## If You Want to Use Alembic with Supabase PostgreSQL

If you want to use Alembic with Supabase's PostgreSQL connection (not REST API):

1. Restore `DATABASE_URL` in `app/core/config.py`
2. Restore SQLAlchemy session management
3. Update `alembic/env.py` to use Supabase PostgreSQL connection string
4. Run `alembic upgrade head`

However, this defeats the purpose of using Supabase REST API, which was chosen to avoid PostgreSQL connection issues.

## Recommendation

**Keep using Supabase REST API** and handle migrations manually through Supabase Dashboard. This is simpler and avoids connection issues.

