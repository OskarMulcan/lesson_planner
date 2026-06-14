from __future__ import annotations

import logging
import typer

from ..logging_setup import configure_logging
from ..database import init_db, clear_data, drop_schema, APP_SCHEMAS

db_app = typer.Typer(help="Database management commands.")

@db_app.command()
def init() -> None:
    """Initialize database schemas, extensions, and create all application tables."""
    configure_logging()
    logger = logging.getLogger(__name__)
    schema_list = ", ".join(APP_SCHEMAS)
    
    typer.echo(f"Creating structures for application schemas: [{schema_list}]...")
    try:
        init_db()
        logger.info("Database initialized successfully.")
        typer.secho("Success: Database initialization complete!", fg=typer.colors.GREEN, bold=True)
    except Exception as exc:
        logger.exception("Database initialization failed: %s", exc)
        typer.secho("Error: Initialization failed!", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@db_app.command()
def clear() -> None:
    """Truncate all data tables across all application schemas (preserves schema layout)."""
    configure_logging()
    logger = logging.getLogger(__name__)
    schema_list = ", ".join(APP_SCHEMAS)
    
    typer.echo(f"Truncating all data tables inside schemas: [{schema_list}]...")
    try:
        clear_data()
        logger.info("Database data cleared.")
        typer.secho("Success: All tables successfully truncated!", fg=typer.colors.GREEN)
    except Exception as exc:
        logger.exception("Database truncation failed: %s", exc)
        typer.secho("Error: Data clearing failed!", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@db_app.command()
def drop(
    reinit: bool = typer.Option(
        False, 
        "--reinit", 
        help="Immediately run 'init' after dropping to provide a fresh, empty workspace."
    )
) -> None:
    """Drop application schemas entirely (destroys data and structural layouts)."""
    configure_logging()
    logger = logging.getLogger(__name__)
    schema_list = ", ".join(APP_SCHEMAS)
    
    typer.echo(f"Dropping application schemas completely: [{schema_list}]...")
    try:
        drop_schema()
        if reinit:
            typer.echo("Re-initializing clean schemas and tables...")
            init_db()
            logger.info("Database schemas dropped and re-initialized via CLI.")
            typer.secho("Success: Application schemas completely reset and re-initialized!", fg=typer.colors.GREEN, bold=True)
        else:
            logger.info("Database schemas dropped via CLI.")
            typer.secho("Warning: Application schemas successfully destroyed.", fg=typer.colors.YELLOW, bold=True)
            
    except Exception as exc:
        logger.exception("Database drop failed: %s", exc)
        typer.secho("Error: Drop layout execution failed!", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)