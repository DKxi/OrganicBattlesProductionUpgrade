import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# 1. Interpret the config file for Python logging.
config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# 2. Add application models' Base metadata for 'autogenerate' support.
from app.infrastructure.database.models import Base
target_metadata = Base.metadata


def get_target_url() -> str:
    """Dynamically resolve database connection URL without hardcoded secrets."""
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        from app.settings import settings
        import app.infrastructure.database.engine as db_engine
        url = db_engine.current_db_url or settings.database_url
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode without an active connection."""
    url = get_target_url()
    is_sqlite = url.startswith("sqlite")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=is_sqlite,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with an engine or connection."""
    # Check if a live connection was passed into config attributes
    passed_connection = config.attributes.get("connection", None)

    if passed_connection is not None:
        is_sqlite = str(passed_connection.engine.url).startswith("sqlite")
        context.configure(
            connection=passed_connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite,
        )
        with context.begin_transaction():
            context.run_migrations()
        return

    # Otherwise build from dynamic URL
    url = get_target_url()
    is_sqlite = url.startswith("sqlite")

    from app.infrastructure.database.engine import build_engine
    connectable = build_engine(url)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
