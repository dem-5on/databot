# Data Bundle Purchase System

A production-ready system for purchasing mobile data bundles via Telegram bot, integrated with Paystack Mobile Money payments and DatamartGH vendor API.

## Features

- **Telegram Bot Interface**: User-friendly bot for bundle purchases
- **Paystack Integration**: Mobile Money payment processing
- **DatamartGH Integration**: Bundle catalog and purchase execution
- **Wallet System**: Internal wallet for managing user balances
- **Admin Notifications**: Telegram alerts for deposits and order failures
- **Database**: PostgreSQL with async SQLAlchemy
- **Migrations**: Alembic for database schema management

## Tech Stack

- **Backend**: FastAPI (async)
- **Database**: PostgreSQL with asyncpg
- **ORM**: SQLAlchemy (async)
- **Migrations**: Alembic
- **Telegram Bot**: python-telegram-bot v20.6
- **Payments**: Paystack Mobile Money
- **Vendor**: DatamartGH API

## Prerequisites

- Python 3.12+
- PostgreSQL 15+
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

### 2. Environment Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:
- `DATABASE_URL`: PostgreSQL connection string
- `PAYSTACK_SECRET_KEY`: Paystack secret key
- `PAYSTACK_PUBLIC_KEY`: Paystack public key
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `TELEGRAM_ADMIN_IDS`: Comma-separated admin Telegram IDs
- `DATAMART_API_KEY`: DatamartGH API key

### 3. Database Setup

```bash
# Run migrations
alembic upgrade head
```

### 4. Run the Application

#### Development Mode

```bash
# Start backend API
uvicorn app.main:app --reload

# In another terminal, start the Telegram bot
python -m bot.telegram_bot
```

#### Docker Compose

```bash
# Build and start all services
docker-compose up --build

# Run migrations in the container
docker-compose exec backend alembic upgrade head
```

## API Endpoints

### Health Check
- `GET /health` - Returns `{"status": "ok"}`

### Wallet
- `POST /api/v1/wallet/deposit/init` - Initiate deposit
- `GET /api/v1/wallet/balance/{telegram_id}` - Get wallet balance

### Orders
- `POST /api/v1/orders` - Create bundle purchase order
- `GET /api/v1/users/{telegram_id}/history` - Get transaction history

### Webhooks
- `POST /api/v1/webhooks/paystack` - Paystack webhook handler

## Project Structure

```
databot/
├── app/
│   ├── api/           # API routes
│   ├── core/          # Core configuration
│   ├── db/            # Database setup
│   ├── models/        # SQLAlchemy models
│   ├── services/      # Business logic
│   └── main.py        # FastAPI app
├── bot/               # Telegram bot
├── alembic/           # Database migrations
├── tests/             # Test files
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Development

### Running Tests

```bash
pytest
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## License

MIT

