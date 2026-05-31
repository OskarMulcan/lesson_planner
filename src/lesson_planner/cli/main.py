from __future__ import annotations

import logging
import click
import typer

from lesson_planner.logging_setup import configure_logging
from lesson_planner.database import init_db

app = typer.Typer()
db_app = typer.Typer()
app.add_typer(db_app, name="db")


def _log_level_callback(ctx: click.Context, param: click.Parameter, value: str) -> str:
    if value:
        configure_logging(value)
    return value


@app.callback(invoke_without_command=True)
def main(
    log_level: str = typer.Option(
        None,
        "--log-level",
        callback=_log_level_callback,
        help="Override log level",
    ),
) -> None:
    """Top level CLI for lesson planner."""
    return None


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
