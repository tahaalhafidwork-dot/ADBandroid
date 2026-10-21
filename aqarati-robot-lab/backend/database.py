"""SQLite connection and transaction helpers."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import Settings


class Base(DeclarativeBase):
    pass


settings = Settings.load()
settings.database_path.parent.mkdir(parents=True, exist_ok=True)
engine: Engine = create_engine(
    "sqlite:///{0}".format(settings.database_path.as_posix()),
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(engine, "connect")
def _configure_sqlite(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def get_session():
    with SessionLocal() as session:
        yield session


def initialize_database() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(engine)
    with SessionLocal.begin() as session:
        from .seed import seed_dialect_terms

        seed_dialect_terms(session)


def session_scope() -> Session:
    """Return a session for scripts; callers must close it."""
    return SessionLocal()

