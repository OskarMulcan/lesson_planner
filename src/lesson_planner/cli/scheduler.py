import typer

scheduler_app = typer.Typer(help="Scheduling commands.")

@scheduler_app.command()
def run() -> None:
    """Run the lesson scheduling algorithm."""
    typer.echo("Scheduler is not implemented yet.")