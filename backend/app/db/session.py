"""
Database engine and session management.

Design decision: we expose a `get_db` dependency (FastAPI generator pattern)
rather than a global session, so each request gets its own SQLAlchemy
session with guaranteed cleanup via try/finally. This avoids cross-request
state leakage and is the standard FastAPI + SQLAlchemy pattern.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

_connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,   # verifies connections are alive before use (avoids stale-connection errors)
    pool_size=10 if not settings.DATABASE_URL.startswith("sqlite") else 1,
    max_overflow=20 if not settings.DATABASE_URL.startswith("sqlite") else 0,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class all ORM models will inherit from
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
