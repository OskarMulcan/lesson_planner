from __future__ import annotations

import typer
from uuid import UUID
from pathlib import Path
from typing import Optional

from ..logging_setup import configure_logging
from ..models import VisualizationDimension

viz_app = typer.Typer(help="Manage and export schedule visualizations.")


@viz_app.command("generate")
def generate_cmd(schedule_id: UUID) -> None:
    """Generate HTML and PNG visualizations for a given schedule."""
    configure_logging()
    from lesson_planner.database import get_session
    from lesson_planner.visualization.generator import generate_visualizations_for_schedule

    with get_session() as session:
        typer.echo(f"Generating visualizations for schedule {schedule_id}...")
        generate_visualizations_for_schedule(session, schedule_id)
        typer.echo("Done.")


@viz_app.command("list")
def list_cmd(
    schedule_id: UUID,
    dimension: Optional[VisualizationDimension] = typer.Option(
        None, help="Filter by dimension (ROOM, CLASS, TEACHER)"
    ),
) -> None:
    """List generated visualizations for a schedule."""
    configure_logging()
    from lesson_planner.database import get_session
    from lesson_planner.visualization.generator import list_visualizations

    with get_session() as session:
        visualizations = list_visualizations(session, schedule_id, dimension)
        if not visualizations:
            typer.echo(f"No visualizations found for schedule {schedule_id}.")
            raise typer.Exit()

        for viz in visualizations:
            has_html = "HTML" if viz.html_content else ""
            has_png = "PNG" if viz.png_content else ""
            formats = "/".join(filter(None, [has_html, has_png])) or "None"
            typer.echo(f"[{viz.dimension.value}] {viz.label} - Formats: {formats}")


@viz_app.command("export")
def export_cmd(
    schedule_id: UUID,
    output_dir: Path = typer.Argument(..., help="Directory to save the exported files"),
    dimension: Optional[VisualizationDimension] = typer.Option(
        None, help="Filter by dimension (ROOM, CLASS, TEACHER)"
    ),
) -> None:
    """Export visualizations to HTML and PNG files on disk."""
    configure_logging()
    from lesson_planner.database import get_session
    from lesson_planner.visualization.generator import export_all_visualizations

    with get_session() as session:
        typer.echo(f"Exporting visualizations to {output_dir}...")
        count = export_all_visualizations(session, schedule_id, output_dir, dimension)
        typer.echo(f"Exported {count} visualizations successfully.")