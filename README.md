# Data Bundle Purchase System

A production-ready system for purchasing mobile data bundles via Telegram bot, integrated with Paystack Mobile Money payments and DatamartGH vendor API.

## Features

- **Telegram Bot Interface**: User-friendly bot for bundle purchases
- **Paystack Integration**: Mobile Money payment processing
- **DatamartGH Integration**: Bundle catalog and purchase execution
- **Wallet System**: Internal wallet for managing user balances
- **Admin Notifications**: Telegram alerts for deposits and order failures
- **Database**: Supabase (managed PostgreSQL with REST API)
- **Referral System**: Users can refer others and earn bonuses

## Tech Stack

- **Backend**: FastAPI (async)
- **Database**: Supabase (REST API)
- **Telegram Bot**: python-telegram-bot v20.6
- **Payments**: Paystack Mobile Money
- **Vendor**: DatamartGH API

## Prerequisites

- Python 3.12+
- Supabase account (free tier works)
- Docker and Docker Compose (optional)
- Telegram Bot Token
- Paystack API Keys
- DatamartGH API Key

## Setup

### 1. Clone and Install Dependencies

```bash
# Create virtual environment
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Supabase Setup

#### 2.1 Create Supabase Project

1. Go to [Supabase](https://supabase.com) and create a new project
2. Wait for the project to be provisioned
3. Go to Settings → API
4. Copy your `Project URL` (SUPABASE_URL)
5. Copy your `anon` key or `service_role` key (SUPABASE_KEY)

#### 2.2 Create Database Tables

Go to Supabase Dashboard → SQL Editor and run the following SQL:

```sql
-- Users table
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

-- Wallets table
CREATE TABLE IF NOT EXISTS wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    balance NUMERIC(10, 2) DEFAULT 0.00 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wallets_user_id ON wallets(user_id);

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('deposit', 'purchase', 'refund', 'referral_bonus')),
    amount NUMERIC(10, 2) NOT NULL,
    currency TEXT DEFAULT 'GHS' NOT NULL,
    reference TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'success', 'failed')),
    phone TEXT,
    provider TEXT,
    raw_payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_reference ON transactions(reference);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);

-- Bundles table
CREATE TABLE IF NOT EXISTS bundles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    network TEXT NOT NULL,
    capacity TEXT NOT NULL,
    mb TEXT NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    currency TEXT DEFAULT 'GHS' NOT NULL,
    active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bundles_network ON bundles(network);
CREATE INDEX IF NOT EXISTS idx_bundles_active ON bundles(active);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bundle_id UUID NOT NULL REFERENCES bundles(id) ON DELETE CASCADE,
    phone TEXT NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'success', 'failed')),
    vendor_reference TEXT,
    vendor_response JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_bundle_id ON orders(bundle_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_vendor_reference ON orders(vendor_reference);

-- Referrals table
CREATE TABLE IF NOT EXISTS referrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    referred_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    referral_code TEXT NOT NULL,
    bonus_paid BOOLEAN DEFAULT FALSE NOT NULL,
    bonus_amount TEXT DEFAULT '0.10' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    bonus_paid_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_referrals_referrer_id ON referrals(referrer_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referred_id ON referrals(referred_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referral_code ON referrals(referral_code);
```

#### 2.3 Configure Row Level Security (RLS)

If you're using the `anon` key (not `service_role`), you need to configure RLS policies:

1. Go to Supabase Dashboard → Authentication → Policies
2. For each table, create policies to allow service role operations
3. Or use `service_role` key to bypass RLS (for backend operations)

### 3. Environment Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```env
# Supabase (Required)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-anon-key-or-service-role-key

# Paystack
PAYSTACK_SECRET_KEY=sk_test_...
PAYSTACK_PUBLIC_KEY=pk_test_...
PAYSTACK_BASE_URL=https://api.paystack.co

# Telegram
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_ADMIN_IDS=123456789,987654321
TELEGRAM_API_URL=https://api.telegram.org/bot

# DatamartGH
DATAMART_API_URL=https://api.datamartgh.shop/api/developer
DATAMART_API_KEY=your-datamart-api-key

# Backend API
BACKEND_API_URL=http://localhost:8000

# Optional Settings
PURCHASE_TIMEOUT=60
MINIMUM_DEPOSIT_AMOUNT=1
```

### 4. Run the Application

#### Development Mode

**Terminal 1 - Start Backend API:**
```bash
# Activate virtual environment
source env/bin/activate  # On Windows: env\Scripts\activate

# Start FastAPI server
uvicorn app.main:app --reload
```

**Terminal 2 - Start Telegram Bot:**
```bash
# Activate virtual environment
source env/bin/activate  # On Windows: env\Scripts\activate

# Start Telegram bot
python -m bot.telegram_bot
```

#### Docker Compose

```bash
# Build and start containers
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

## Testing

### Test Database Connection

```bash
python -c "from app.db.supabase_client import supabase; print('Connected!')"
```

### Test API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Create user
curl -X POST "http://localhost:8000/api/v1/users/ensure?telegram_id=123&name=Test"

# Get balance
curl http://localhost:8000/api/v1/wallet/balance/123

# Get bundles
curl http://localhost:8000/api/v1/bundles
```

## Project Structure

```
databot/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── users.py          # User endpoints
│   │       ├── wallet.py         # Wallet endpoints
│   │       ├── orders.py         # Order endpoints
│   │       ├── bundles.py        # Bundle endpoints
│   │       ├── referrals.py      # Referral endpoints
│   │       ├── webhooks/
│   │       │   └── paystack.py   # Paystack webhook
│   │       └── admin/
│   │           └── tasks.py      # Admin tasks
│   ├── core/
│   │   └── config.py             # Settings
│   ├── db/
│   │   └── supabase_client.py    # Supabase client
│   ├── models/                   # SQLAlchemy models (reference only)
│   ├── repository/               # Supabase repositories
│   │   ├── base.py
│   │   ├── user_repo.py
│   │   ├── wallet_repo.py
│   │   ├── transaction_repo.py
│   │   ├── bundle_repo.py
│   │   ├── order_repo.py
│   │   └── referral_repo.py
│   ├── services/                 # Business logic
│   │   ├── wallet_service.py
│   │   ├── order_service.py
│   │   ├── referral_service.py
│   │   ├── bundle_sync.py
│   │   ├── paystack_service.py
│   │   ├── datamart_client.py
│   │   ├── notifier.py
│   │   └── scheduler.py
│   ├── main.py                   # FastAPI app
│   └── entrypoint.sh             # Docker entrypoint
├── bot/
│   ├── telegram_bot.py           # Bot application
│   ├── keyboard.py               # Keyboards
│   └── handlers/                 # Bot handlers
│       ├── start.py
│       ├── balance.py
│       ├── deposit.py
│       ├── bundles.py
│       ├── history.py
│       ├── referral.py
│       └── help.py
├── tests/                        # Tests
├── docker-compose.yml            # Docker Compose config
├── Dockerfile                    # Docker image
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## API Endpoints

### User Endpoints
- `POST /api/v1/users/ensure` - Ensure user exists
- `GET /api/v1/users/{telegram_id}/history` - Get user history

### Wallet Endpoints
- `POST /api/v1/wallet/deposit/init` - Initialize deposit
- `POST /api/v1/wallet/deposit/confirm` - Confirm deposit with OTP
- `GET /api/v1/wallet/balance/{telegram_id}` - Get wallet balance

### Order Endpoints
- `POST /api/v1/orders` - Create bundle purchase order

### Bundle Endpoints
- `GET /api/v1/bundles` - Get available bundles

### Referral Endpoints
- `GET /api/v1/referrals/code/{telegram_id}` - Get referral code
- `GET /api/v1/referrals/referrals/{telegram_id}` - Get referrals list

### Webhook Endpoints
- `POST /api/v1/webhooks/paystack` - Paystack webhook handler

### Admin Endpoints
- `POST /api/v1/admin/sync-bundles` - Sync bundles from DatamartGH
- `GET /api/v1/admin/health/datamart` - Check DatamartGH health
- `GET /api/v1/admin/health/paystack` - Check Paystack health

## Database Migrations

**Note:** Since we're using Supabase REST API, database migrations are handled via Supabase Dashboard SQL Editor, not Alembic.

See `ALEMBIC_MIGRATION_NOTES.md` for details.

## Troubleshooting

### Supabase Connection Issues

- Check `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
- Verify credentials in Supabase dashboard
- Ensure tables are created in Supabase
- Check RLS policies if using `anon` key

### Table Not Found Errors

- Run the SQL scripts in Supabase SQL Editor
- Verify table names match your repository expectations
- Check RLS policies

### Permission Issues

- Use `service_role` key for backend operations (bypasses RLS)
- Or configure RLS policies for `anon` key

### Bot Not Responding

- Check `TELEGRAM_BOT_TOKEN` in `.env`
- Verify bot is running: `python -m bot.telegram_bot`
- Check backend API is running: `curl http://localhost:8000/health`

## Development Guidelines

### Adding New Features

1. Create repository methods in `app/repository/`
2. Create service methods in `app/services/`
3. Create API endpoints in `app/api/v1/`
4. Update bot handlers if needed

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app
```

## License

MIT

## Support

For issues or questions:
- Check Supabase documentation: https://supabase.com/docs
- Check Paystack documentation: https://paystack.com/docs
- Check DatamartGH documentation: https://www.datamartgh.shop/api-doc
