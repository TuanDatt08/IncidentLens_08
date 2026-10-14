import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.config import cloud_database_url, get_settings
from backend.models import (
    auth,  # noqa: F401 - register auth metadata
    tables_v2,  # noqa: F401 - register additive V2 metadata
)
from backend.models.tables import Base

config = context.config
target_metadata = Base.metadata


def get_url():
    settings = get_settings()
    url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url") or settings.database_url
    return cloud_database_url(url) if settings.database_cloud else url


def run_migrations_offline():
    context.configure(url=get_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
