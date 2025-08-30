from __future__ import annotations
import os, sys
from pathlib import Path
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv

# ── Locate project root for this Alembic instance (api\)
API_DIR = Path(__file__).resolve().parents[1]  # ...\api
# Load .env from api\
load_dotenv(API_DIR / ".env")

# Alembic Config object
config = context.config

# Inject DB URL from .env into Alembic
db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise RuntimeError("DATABASE_URL not set in .env")
config.set_main_option("sqlalchemy.url", db_url)

# Ensure Python can import your application modules
sys.path.insert(0, str(API_DIR))

# Import Base + models so Alembic can see them
from models import Base  # declarative_base() lives here
import models  # ensures Stock and any future models are registered

# Interpret Alembic config file for logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point Alembic’s autogenerate at your models’ metadata
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
