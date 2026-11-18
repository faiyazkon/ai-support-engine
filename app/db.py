"""Database connection. SQLAlchemy lets the same code run on SQLite now and PostgreSQL later.

Only DATABASE_URL in .env decides which one. SQLite is one file (data/support.db) and needs no server.
"""
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine():
    url = make_url(get_settings().database_url)
    kwargs = {}
    if url.get_backend_name() == "sqlite":
        kwargs["connect_args"] = {"check_same_thread": False}
        if url.database in (None, "", ":memory:"):
            kwargs["poolclass"] = StaticPool  # an in-memory database lives in one connection (used by tests)
        else:
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, **kwargs)

    if url.get_backend_name() == "sqlite":
        @event.listens_for(engine, "connect")
        def _sqlite_settings(dbapi_connection, _):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")    # readers and a writer don't block each other
            cursor.execute("PRAGMA foreign_keys=ON")     # SQLite ignores foreign keys unless told to check
            cursor.execute("PRAGMA busy_timeout=5000")   # wait up to 5 s instead of failing when the file is busy
            cursor.close()
    return engine


@lru_cache
def get_session_factory():
    return sessionmaker(get_engine(), expire_on_commit=False)


def init_db() -> None:
    from app import models  # noqa: F401  (importing registers the tables)

    Base.metadata.create_all(get_engine())
