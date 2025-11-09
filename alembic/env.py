"""
Alembic Environment - DEPRECATED

This file is no longer used since we migrated to Supabase REST API.
Database migrations are now handled via Supabase Dashboard SQL Editor.

See ALEMBIC_MIGRATION_NOTES.md for details.
"""

# NOTE: This file is kept for reference only and will not work with current configuration
# because we removed DATABASE_URL and database_url property from settings.

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import models and base (these may not work with current setup)
# from app.db.base import Base
# from app.models import User, Wallet, Transaction, Bundle, Order  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# NOTE: The following will fail because we removed DATABASE_URL from settings
# This file is kept for reference only
# Import settings to get DATABASE_URL
# from app.core.config import settings

# Set the database URL from settings (use database_url property)
# config.set_main_option("sqlalchemy.url", settings.database_url)

# add your model's MetaData object here
# for 'autogenerate' support
# target_metadata = Base.metadata
target_metadata = None  # Not used anymore

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """
    DEPRECATED: Alembic migrations are no longer used.
    Database migrations are handled via Supabase Dashboard SQL Editor.
    """
    raise RuntimeError(
        "❌ Alembic is no longer used with Supabase REST API.\n\n"
        "Database migrations are now handled via Supabase Dashboard SQL Editor.\n"
        "See ALEMBIC_MIGRATION_NOTES.md for details on how to create tables.\n\n"
        "To create tables:\n"
        "1. Go to Supabase Dashboard → SQL Editor\n"
        "2. Run SQL migration scripts\n"
        "3. Tables will be created in Supabase"
    )


def do_run_migrations(connection: Connection) -> None:
    """
    DEPRECATED: Alembic migrations are no longer used.
    """
    raise RuntimeError(
        "Alembic is no longer used. Use Supabase Dashboard SQL Editor for migrations."
    )


async def run_async_migrations() -> None:
    """
    DEPRECATED: Alembic migrations are no longer used.
    """
    raise RuntimeError(
        "Alembic is no longer used. Use Supabase Dashboard SQL Editor for migrations."
    )


def run_migrations_online() -> None:
    """
    DEPRECATED: Alembic migrations are no longer used.
    """
    raise RuntimeError(
        "❌ Alembic is no longer used with Supabase REST API.\n\n"
        "Database migrations are now handled via Supabase Dashboard SQL Editor.\n"
        "See ALEMBIC_MIGRATION_NOTES.md for details."
    )


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
