"""Database session factory. Schema changes are applied by Alembic, not startup."""

from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings


@lru_cache
def get_session_factory(url: str | None = None) -> sessionmaker[Session]:
    database_url = url or get_settings().database_url
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope():
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
