# Quick Start Guide

## Prerequisites Checklist

- [ ] Python 3.12+ installed
- [ ] Supabase account created
- [ ] Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- [ ] Paystack API Keys (from [Paystack Dashboard](https://dashboard.paystack.com))
- [ ] DatamartGH API Key (from [DatamartGH](https://www.datamartgh.shop))

## Step-by-Step Setup

### 1. Clone and Setup Python Environment

```bash
# Navigate to project directory
cd databot

# Create virtual environment
python -m venv env

# Activate virtual environment
# On Linux/Mac:
source env/bin/activate
# On Windows:
env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup Supabase

#### 2.1 Create Supabase Project

1. Go to [https://supabase.com](https://supabase.com)
2. Click "New Project"
3. Fill in project details and wait for provisioning
4. Go to **Settings → API**
5. Copy:
   - **Project URL** (e.g., `https://xxxxx.supabase.co`)
   - **anon key** or **service_role key**

#### 2.2 Create Database Tables

1. Go to **SQL Editor** in Supabase Dashboard
2. Copy and paste the SQL from `README.md` (section 2.2)
3. Click **Run** to execute
4. Verify tables are created in **Table Editor**

### 3. Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env file with your credentials
nano .env  # or use your favorite editor
```

Fill in `.env`:

```env
# Supabase (Required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key

# Paystack
PAYSTACK_SECRET_KEY=sk_test_your_secret_key
PAYSTACK_PUBLIC_KEY=pk_test_your_public_key

# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_ADMIN_IDS=123456789

# DatamartGH
DATAMART_API_KEY=your_datamart_api_key

# Backend (default is fine for local)
BACKEND_API_URL=http://localhost:8000
```

### 4. Test Supabase Connection

```bash
python -c "from app.db.supabase_client import supabase; print('✅ Connected to Supabase!')"
```

If you see an error, check:
- SUPABASE_URL and SUPABASE_KEY are correct
- Tables are created in Supabase
- Internet connection is working

### 5. Run the Application

#### Option A: Development Mode (Recommended)

**Terminal 1 - Start Backend:**
```bash
# Make sure virtual environment is activated
source env/bin/activate

# Start FastAPI server
uvicorn app.main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

**Terminal 2 - Start Telegram Bot:**
```bash
# Make sure virtual environment is activated
source env/bin/activate

# Start Telegram bot
python -m bot.telegram_bot
```

You should see:
```
Application started. Press Ctrl+C to stop.
```

#### Option B: Docker Compose

```bash
# Build and start
docker-compose up --build

# View logs
docker-compose logs -f backend
docker-compose logs -f bot  # if you have bot in docker
```

### 6. Test the System

#### Test Backend API

```bash
# Health check
curl http://localhost:8000/health

# Expected response: {"status":"ok"}

# Create a user
curl -X POST "http://localhost:8000/api/v1/users/ensure?telegram_id=123456789&name=TestUser"

# Get bundles
curl http://localhost:8000/api/v1/bundles
```

#### Test Telegram Bot

1. Open Telegram
2. Search for your bot (the username you set with BotFather)
3. Send `/start` command
4. You should see the welcome message and keyboard

### 7. Sync Bundles (First Time)

```bash
# Sync bundles from DatamartGH to database
curl -X POST "http://localhost:8000/api/v1/admin/sync-bundles"

# Or use the sync endpoint
curl -X POST "http://localhost:8000/sync/bundles"
```

### 8. Configure Paystack Webhook (Optional but Recommended)

1. Go to [Paystack Dashboard](https://dashboard.paystack.com)
2. Navigate to **Settings → Webhooks**
3. Add webhook URL: `https://your-domain.com/api/v1/webhooks/paystack`
4. Select events: `charge.success`, `charge.failed`
5. Copy the webhook secret (if provided)

**For local development:**
- Use [ngrok](https://ngrok.com) to expose your local server
- Or use Paystack's test webhook endpoint

## Common Issues

### Issue: "Failed to initialize Supabase client"

**Solution:**
- Check SUPABASE_URL and SUPABASE_KEY in `.env`
- Verify credentials in Supabase dashboard
- Make sure there are no extra spaces in `.env` file

### Issue: "Table 'users' does not exist"

**Solution:**
- Run the SQL scripts in Supabase SQL Editor
- Verify tables are created in Table Editor
- Check table names match (case-sensitive)

### Issue: "Bot not responding"

**Solution:**
- Check TELEGRAM_BOT_TOKEN in `.env`
- Verify bot is running: `python -m bot.telegram_bot`
- Check backend API is running: `curl http://localhost:8000/health`
- Check bot logs for errors

### Issue: "Permission denied for table"

**Solution:**
- Use `service_role` key instead of `anon` key (bypasses RLS)
- Or configure RLS policies in Supabase Dashboard

### Issue: "Bundles not showing"

**Solution:**
- Sync bundles: `curl -X POST "http://localhost:8000/api/v1/admin/sync-bundles"`
- Check DatamartGH API key is correct
- Check DatamartGH API is accessible

## Next Steps

1. **Test Deposit Flow:**
   - Use the bot to deposit money
   - Complete the Paystack payment
   - Verify wallet is credited

2. **Test Bundle Purchase:**
   - Browse bundles in the bot
   - Purchase a bundle
   - Verify order is created

3. **Monitor Logs:**
   - Check backend logs for errors
   - Check bot logs for errors
   - Check Supabase logs in dashboard

4. **Setup Production:**
   - Use production Paystack keys
   - Use production Supabase project
   - Configure webhooks properly
   - Setup domain and SSL

## Getting Help

- Check `README.md` for detailed documentation
- Check `SUPABASE_MIGRATION_GUIDE.md` for Supabase setup
- Check `ALEMBIC_MIGRATION_NOTES.md` for database migration info
- Review error logs for specific issues

## Useful Commands

```bash
# Test Supabase connection
python -c "from app.db.supabase_client import supabase; print('Connected!')"

# Sync bundles
curl -X POST "http://localhost:8000/api/v1/admin/sync-bundles"

# Check health
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs

# Run tests
pytest

# Check logs (Docker)
docker-compose logs -f backend
```

