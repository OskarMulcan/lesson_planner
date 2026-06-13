import logging
import typer

from lesson_planner.logging_setup import configure_logging
from lesson_planner.database import init_db, clear_data, drop_schema

db_app = typer.Typer(help="Database management commands.")

@db_app.command()
def init() -> None:
    """Initialize the database schema."""
    logger = logging.getLogger(__name__)
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as exc:
        logger.exception("Database initialization failed: %s", exc)
        raise typer.Exit(code=1)


@db_app.command()
def drop(reinit: bool = typer.Option(False, "--reinit", help="Drop whole schema and re-initialize DB from models")) -> None:
    """Clear all data (truncate tables) or drop schema and optionally reinitialize DB."""
    configure_logging()
    logger = logging.getLogger(__name__)
    try:
        if reinit:
            logger.info("Dropping public schema and recreating it")
            drop_schema()
            init_db()
            logger.info("Database schema dropped and re-initialized successfully")
        else:
            logger.info("Clearing all data from database tables")
            clear_data()
            logger.info("Database data cleared (tables truncated)")
    except Exception as exc:
        logger.exception("Database drop failed: %s", exc)
        raise typer.Exit(code=1)