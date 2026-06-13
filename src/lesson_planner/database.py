from __future__ import annotations

import logging
from typing import Optional
from collections.abc import Generator
from contextlib import contextmanager
from sqlalchemy import create_engine, text, Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session

from .config import settings
from .models import Base 

logger = logging.getLogger(__name__)

_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker[Session]] = None

APP_SCHEMAS = ["facilities", "academic", "staff", "schedule", "integration"]


def get_engine() -> Engine:
    """Lazily initialize and return the database engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(settings.database_url, echo=False)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Lazily initialize and return the session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(), 
            expire_on_commit=False, 
            autoflush=False
        )
    return _session_factory


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Provide a transactional database session."""
    factory = get_session_factory()
    with factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def init_db() -> None:
    """Initialize database schemas, extensions, and create all tables."""
    try:
        engine = get_engine()
        with engine.begin() as conn:
            # 1. Explicitly create schemas first
            for schema in APP_SCHEMAS:
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
                
            # 2. Create required extensions
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
            
            # 3. Create tables
            Base.metadata.create_all(bind=conn)
            
    except SQLAlchemyError as exc:
        logger.error("Database initialization failed: %s", exc)
        raise


def clear_data() -> None:
    """Truncate all tables across all schemas, restarting identities."""
    try:
        from sqlalchemy import MetaData

        engine = get_engine()
        
        with engine.begin() as conn:
            schemas_to_clear = APP_SCHEMAS if APP_SCHEMAS else [None]
            all_tables = []
            
            for schema in schemas_to_clear:
                metadata = MetaData(schema=schema)
                metadata.reflect(bind=conn)
                for t in metadata.sorted_tables:
                    table_name = f'"{t.schema}"."{t.name}"' if t.schema else f'"{t.name}"'
                    all_tables.append(table_name)

            if not all_tables:
                logger.info("No tables found to truncate.")
                return

            table_list = ", ".join(all_tables)
            conn.execute(text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE"))
            
    except SQLAlchemyError as exc:
        logger.error("Failed to clear database data: %s", exc)
        raise


def drop_schema() -> None:
    """Drop schemas completely and recreate them."""
    try:
        engine = get_engine()
        with engine.begin() as conn:
            schemas_to_drop = APP_SCHEMAS if APP_SCHEMAS else ["public"]
            
            for schema in schemas_to_drop:
                conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
                conn.execute(text(f"CREATE SCHEMA {schema}"))
                
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
    except SQLAlchemyError as exc:
        logger.error("Failed to drop/create schemas: %s", exc)
        raise