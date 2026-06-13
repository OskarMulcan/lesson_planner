import typer
from pathlib import Path

from lesson_planner.logging_setup import configure_logging
from lesson_planner.database import get_session
from lesson_planner.data_imports.base import run_import, log_summary

from lesson_planner.data_imports import IMPORT_REGISTRY

import_app = typer.Typer(help="Data import commands.")


def _register_import_command(target_name: str, handler) -> None:
    """
    Factory function to dynamically generate and register a Typer command.
    Using a factory function prevents Python's late-binding loop closures 
    from assigning the last item in the loop to all commands.
    """
    cmd_name = target_name.replace("_", "-")
    
    try:
        columns = ",".join(handler.row_model.model_fields.keys())
    except AttributeError:
        columns = ",".join(handler.row_model.__fields__.keys())

    @import_app.command(cmd_name)
    def _import_cmd(
        path: Path = typer.Argument(..., help=f"Path to the {cmd_name} CSV file.", exists=True)
    ) -> None:
        configure_logging()
        with get_session() as session:
            results = run_import(
                session=session, 
                path=path, 
                target_table=target_name, 
                row_model=handler.row_model, 
                upsert_fn=handler.upsert_fn
            )
            log_summary(results, target_name)
            
            if any(r.status.value == "failed" for r in results):
                raise typer.Exit(code=1)

    _import_cmd.__doc__ = f"""
    Import {target_name.replace('_', ' ')} from CSV.
    
    Expected CSV columns: {columns}
    """


for name, handler in IMPORT_REGISTRY.items():
    _register_import_command(name, handler)