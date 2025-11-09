# Supabase Integration Guide

This document explains how the Supabase integration works in this project.

## Overview

The project supports two ways to connect to Supabase:

1. **PostgreSQL Connection (Recommended)**: Use Supabase as a managed PostgreSQL database with SQLAlchemy ORM
2. **REST API**: Use Supabase REST API for specific features (optional)

## Architecture

- **SQLAlchemy ORM**: All database operations use SQLAlchemy with asyncpg driver
- **Supabase PostgreSQL**: Managed PostgreSQL database hosted on Supabase
- **Supabase REST API**: Optional client for REST API features (currently not used in main codebase)

## Configuration

### Option 1: Direct Connection String (Recommended)

Get the connection string from Supabase dashboard:
1. Go to Settings -> Database
2. Copy the "Connection string" (URI format)
3. Use the "Connection pooling" mode for better performance

Add to `.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres?sslmode=require
```

### Option 2: Supabase Credentials

If you prefer to construct the connection string from individual credentials:

Add to `.env`:
```env
# Supabase REST API (optional, for REST API features)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-anon-key

# Supabase PostgreSQL Connection
SUPABASE_DB_HOST=db.xxxxx.supabase.co
SUPABASE_DB_PASSWORD=your-database-password
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PORT=5432
```

## How It Works

### Database Connection

1. **Config (`app/core/config.py`)**: 
   - Checks for `DATABASE_URL` first
   - Falls back to constructing from Supabase credentials
   - Automatically adds SSL requirement for Supabase connections

2. **Session (`app/db/session.py`)**:
   - Creates SQLAlchemy async engine using the database URL
   - Uses asyncpg driver for async PostgreSQL connections
   - Configures connection pooling for performance

3. **Migrations (`alembic/env.py`)**:
   - Uses the same database URL for migrations
   - Supports both direct connection and Supabase

### Supabase REST API Client

The Supabase REST API client (`app/db/supabase_client.py`) is initialized if:
- `SUPABASE_URL` and `SUPABASE_KEY` are provided
- It's optional and doesn't affect the main database operations

## Benefits of This Approach

1. **Keep Existing Code**: All SQLAlchemy code works without changes
2. **Managed Database**: Supabase handles backups, scaling, and maintenance
3. **SSL Security**: Automatic SSL encryption for connections
4. **Connection Pooling**: Built-in connection pooling for performance
5. **Migration Support**: Alembic migrations work seamlessly
6. **Flexibility**: Can switch between Supabase and other PostgreSQL databases

## Docker Setup

When using Supabase, you don't need the local PostgreSQL service in `docker-compose.yml`.

The `depends_on` for postgres is commented out. If you're using Supabase, you can remove the postgres service entirely from docker-compose.yml.

## Migration from Local PostgreSQL

1. Get your Supabase connection string
2. Update `.env` with `DATABASE_URL` or Supabase credentials
3. Run migrations: `alembic upgrade head`
4. Verify connection: The entrypoint script tests the connection on startup

## Troubleshooting

### Connection Errors

- **SSL Required**: Make sure `sslmode=require` is in your connection string
- **Password Encoding**: Special characters in passwords are automatically URL-encoded
- **Host Format**: Use the database host (e.g., `db.xxxxx.supabase.co`), not the API URL

### Migration Issues

- Ensure your Supabase database has the necessary permissions
- Check that the connection string is correct
- Verify SSL is enabled (required for Supabase)

### REST API Issues

- The REST API client is optional
- If not configured, the application will continue to work with SQLAlchemy
- Check that `SUPABASE_URL` and `SUPABASE_KEY` are correct if using REST API features

## Environment Variables Reference

```env
# Required: Database connection (choose one)
DATABASE_URL=postgresql+asyncpg://...
# OR
SUPABASE_DB_HOST=db.xxxxx.supabase.co
SUPABASE_DB_PASSWORD=your-password
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PORT=5432

# Optional: Supabase REST API
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-anon-key
```

## Notes

- The `UserRepository` class uses Supabase REST API but is currently not used in the main codebase
- All database operations use SQLAlchemy ORM for consistency
- Supabase REST API can be used for future features if needed
- The connection supports both direct connection and connection pooling modes

