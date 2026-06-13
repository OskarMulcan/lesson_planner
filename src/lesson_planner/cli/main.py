import typer

from lesson_planner.logging_setup import configure_logging

from .db import db_app
from .imports import import_app
from .scheduler import scheduler_app

app = typer.Typer(help="Lesson Planner CLI")

app.add_typer(db_app, name="db")
app.add_typer(import_app, name="import")
app.add_typer(scheduler_app, name="schedule")


def _log_level_callback(ctx: typer.Context, value: str) -> str:
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


if __name__ == "__main__":
    app()