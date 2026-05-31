from __future__ import annotations

from contextlib import contextmanager
from typing import Generator
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session

from .config import settings

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None


def _get_engine():
    """Lazily initialize and return the database engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(settings.database_url, future=True)
    return _engine


def _get_session_factory():
    """Lazily initialize and return the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=_get_engine(), expire_on_commit=False, class_=Session
        )
    return _SessionLocal


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Provide a transactional database session.

    Yields:
        SQLAlchemy Session instance that commits on success and rolls back on
        exception.
    """
    session: Session = _get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Initialize database extensions and create all tables.

    The function creates the btree_gist extension then issues metadata
    create_all. Failures are logged as warnings.

    Args:
        None

    Returns:
        None
    """
    try:
        from .models import Base

        engine = _get_engine()
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
            Base.metadata.create_all(bind=conn)
    except SQLAlchemyError as exc:
        logger.warning("Database initialization may have failed: %s", exc)
    except Exception as exc:
        logger.warning("Unexpected error during DB init: %s", exc)
