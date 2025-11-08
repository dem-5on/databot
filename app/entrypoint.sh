#!/bin/bash
set -e  # Exit on error

echo "Starting entrypoint script..."

# Wait for postgres to be ready
echo "Waiting for PostgreSQL to be ready..."
until nc -z postgres 5432; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is up - checking if it's accepting connections..."
sleep 2

# Run migrations
echo "Running database migrations..."
alembic upgrade head || {
  echo "Migration failed! Retrying in 5 seconds..."
  sleep 5
  alembic upgrade head || {
    echo "Migration failed again. Exiting."
    exit 1
  }
}

echo "Migrations completed successfully!"

# Start the application
echo "Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000