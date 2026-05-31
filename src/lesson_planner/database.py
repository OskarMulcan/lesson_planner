from __future__ import annotations

from contextlib import contextmanager
from typing import Generator
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session

from .config import settings

logger = logging.getLogger(__name__)

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Provide a transactional database session.

    Yields:
        SQLAlchemy Session instance that commits on success and rolls back on
        exception.
    """
    session: Session = SessionLocal()
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

        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
            Base.metadata.create_all(bind=conn)
    except SQLAlchemyError as exc:
        logger.warning("Database initialization may have failed: %s", exc)
    except Exception as exc:
        logger.warning("Unexpected error during DB init: %s", exc)
