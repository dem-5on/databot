# Data Bundle Purchase System

A production-ready system for purchasing mobile data bundles via WhatsApp and Telegram bots, integrated with Paystack Mobile Money payments and DatamartGH vendor API.

## Features

- **WhatsApp & Telegram Bot Interfaces**: User-friendly bots for seamless bundle purchases.
- **WhatsApp Flows**: Native, interactive experiences for users utilizing WhatsApp.
- **Paystack Integration**: Mobile Money payment processing.
- **DatamartGH Integration**: Bundle catalog and purchase execution via API.
- **Wallet System**: Internal wallet for managing user balances.
- **Background Tasks & Scheduler**: Celery workers robustly handle long-running operations, sync tasks, and system health checks.
- **Admin Notifications**: Alerts for deposits and order failures.
- **Database**: Supabase (managed PostgreSQL with REST API).
- **Referral System**: Users can refer others and earn bonuses.

## Tech Stack

- **Backend**: FastAPI (async)
- **Background Tasks/Workers**: Celery, Redis
- **Database**: Supabase (REST API)
- **Telegram Bot**: python-telegram-bot v20.6
- **WhatsApp Bot**: Meta Graph API / WhatsApp Flows
- **Payments**: Paystack Mobile Money
- **Vendor**: DatamartGH API

## Prerequisites

- Python 3.12+
- Supabase account (free tier works)
- Docker and Docker Compose (optional)
- Redis server (for Celery)
- Telegram Bot Token
- WhatsApp Business API Credentials
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

Go to Supabase Dashboard → SQL Editor and run the SQL scripts included in this repository to set up and seed your database:

1. Execute the contents of `schema.sql` to create all required tables (Users, Wallets, Transactions, Bundles, Orders, Referrals) and functions.
2. Execute the contents of `seed_bundles.sql` if you want to prepopulate the bundle database with default options.

#### 2.3 Configure Row Level Security (RLS)

If you're using the `anon` key (not `service_role`), you need to configure RLS policies:

1. Go to Supabase Dashboard → Authentication → Policies
2. For each table, create policies to allow operations
3. Or better yet: use the `service_role` key to bypass RLS for internal backend operations.

### 3. Environment Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual values (see `.env.example` for comprehensive options).

### 4. Run the Application

#### Development Mode

**Terminal 1 - Start Backend API:**

```bash
source env/bin/activate
uvicorn app.main:app --reload
```

**Terminal 2 - Start Telegram Bot:**

```bash
source env/bin/activate
python -m bot.telegram_bot
```

**Terminal 3 - Start WhatsApp Bot:**

```bash
source env/bin/activate
python -m whatsapp.whatsapp_bot
```

**Terminal 4 - Start Celery Workers:**

```bash
source env/bin/activate
# Run Celery worker and beat scheduler
celery -A app.celery_app worker --loglevel=info
celery -A app.celery_app beat --loglevel=info
```

#### Docker Compose

```bash
# Build and start containers
docker-compose up -d --build

# View logs
docker-compose logs -f
```

## Testing

### Expected Commands

```bash
# Run tests
pytest

# Run with coverage target
pytest --cov=app

# Use the test runner script
./run_tests.sh
```

## Project Structure

```text
databot/
├── app/                  # Main FastAPI application & core logic
│   ├── api/              # API Endpoints (v1)
│   ├── core/             # Configuration
│   ├── db/               # Supabase client
│   ├── repository/       # Data access layer
│   ├── services/         # Business logic
│   ├── tasks/            # Background tasks and health monitors
│   └── celery_app.py     # Celery application initialization
├── bot/                  # Telegram Bot source
├── whatsapp/             # WhatsApp integration & Flows
├── tests/                # Test suite
├── scripts/              # Helper scripts
├── schema.sql            # Database schema
├── seed_bundles.sql      # Database default bundle seeding script
├── docker-compose.yml    # Docker configuration
└── requirements.txt      # Project dependencies
```

## Troubleshooting

- **Table Not Found Errors**: Make sure you have run `schema.sql` in the Supabase SQL Editor.
- **Bot Not Responding**: Ensure API keys (`TELEGRAM_BOT_TOKEN`, `WHATSAPP_TOKEN`) are properly set and the respective terminal sessions are running. Also check if ngrok is running and tunneling requests to your bot webhook endpoint properly.
- **Permission Issues / RLS Violations**: Utilize the Supabase service role key for internal requests to avoid RLS blockages on database writes.

## License

MIT
