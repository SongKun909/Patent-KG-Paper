"""SQLAlchemy database engine and session management.

Uses PostgreSQL in production, SQLite for dev/tests.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings

_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        db_url = settings.DATABASE_URL
        if db_url.startswith("sqlite"):
            _engine = create_engine(
                db_url, echo=False, connect_args={"check_same_thread": False}
            )
        else:
            _engine = create_engine(db_url, echo=False, pool_size=10)
    return _engine


def _get_sessionmaker():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())
    return _SessionLocal


def get_db() -> Session:
    db = _get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()


def new_session() -> Session:
    """Create a new session for background tasks (non-request)."""
    return _get_sessionmaker()()
