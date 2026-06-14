from __future__ import annotations

import logging
import uuid
from typing import Annotated
import typer

from ..logging_setup import configure_logging
from ..database import get_session
from ..scheduler import (
    build_scheduling_context,
    MASTER_CONSTRAINT_REGISTRY,
    GeneticEngine,
    SchedulePersister,
)
from ..models.scheduling import Schedule


scheduler_app = typer.Typer(help="Scheduling commands.")
logger = logging.getLogger(__name__)


@scheduler_app.command()
def run(
    name: Annotated[str, typer.Option("--name", "-n", help="Name to save the generated schedule as")],
    population_size: Annotated[int, typer.Option(help="Size of the GA population")] = 50,
    tournament_size: Annotated[int, typer.Option(help="Size of the tournament selection")] = 5,
    mutation_rate: Annotated[float, typer.Option(help="Probability of mutation")] = 0.1,
    repair_every_n: Annotated[int, typer.Option(help="Generations between repairs")] = 10,
    max_generations: Annotated[int, typer.Option(help="Maximum number of generations to run")] = 100,
    fitness_threshold: Annotated[float, typer.Option(help="Target fitness to stop early (lower is better)")] = 0.0,
    elite_size: Annotated[int, typer.Option(help="Number of elite chromosomes to keep")] = 1,
    final_repair_attempts: Annotated[int, typer.Option(help="Number of final repair attempts per candidate")] = 25,
    final_candidates: Annotated[int, typer.Option(help="Number of final candidates from which the best schedule is chosen")] = 5,
    set_active: Annotated[bool, typer.Option("--active", help="Set the generated schedule as active")] = False,
) -> None:
    """Run the genetic lesson scheduling algorithm."""
    configure_logging()
    
    with get_session() as session:
        typer.echo("Building scheduling context from database...")
        context = build_scheduling_context(session)

        typer.echo(f"Initializing Genetic Engine (Max Generations: {max_generations})...")
        engine = GeneticEngine(
            context=context,
            registry=MASTER_CONSTRAINT_REGISTRY,
            population_size=population_size,
            tournament_size=tournament_size,
            mutation_rate=mutation_rate,
            repair_every_n=repair_every_n,
            max_generations=max_generations,
            fitness_threshold=fitness_threshold,
            elite_size=elite_size,
            final_repair_attempts=final_repair_attempts,
            final_candidates=final_candidates,
        )

        typer.echo("Running scheduling algorithm. This may take a while...")
        best_chromosome = engine.run()

        if best_chromosome:
            typer.echo(f"Algorithm finished. Best fitness achieved: {best_chromosome.fitness}")

            typer.echo(f"Persisting schedule as '{name}'...")
            schedule = SchedulePersister.persist(
                session=session,
                chromosome=best_chromosome,
                schedule_name=name,
                is_active=set_active,
            )

            if schedule:
                typer.secho(f"Successfully saved schedule '{name}' with ID: {schedule.id}", fg=typer.colors.GREEN)
            else:
                typer.secho(f"Failed to save schedule '{name}'.", fg=typer.colors.RED)
        else:
            typer.secho("Algorithm finished. No valid schedule was achieved.", fg=typer.colors.RED)


@scheduler_app.command()
def check(
    schedule_id_str: Annotated[str, typer.Argument(help="The UUID of the schedule to validate")],
) -> None:
    """Evaluate a saved schedule and list all current rule and penalty violations."""
    configure_logging()

    try:
        schedule_id = uuid.UUID(schedule_id_str)
    except ValueError:
        typer.secho(f"Error: '{schedule_id_str}' is not a valid UUID format.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    with get_session() as session:
        schedule_meta = session.query(Schedule).filter(Schedule.id == schedule_id).one_or_none()
        if not schedule_meta:
            typer.secho(f"Error: Schedule with ID {schedule_id} not found.", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        typer.echo(f"Loading and mapping data layers for schedule: '{schedule_meta.name}'...")
        
        try:
            chromosome, context = SchedulePersister.load_from_db(session, schedule_id)
        except ValueError as e:
            typer.secho(f"Error loading schedule: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        if not chromosome.lessons:
            typer.secho("Warning: This schedule contains zero complete, active structural entries.", fg=typer.colors.YELLOW)
            raise typer.Exit()

        typer.echo("Running validation suite against master constraint registry...")
        result = MASTER_CONSTRAINT_REGISTRY.evaluate(chromosome, context)

        typer.echo("-" * 60)
        typer.echo(f"DIAGNOSTIC REPORT FOR: {schedule_meta.name}")
        typer.echo(f"Overall Penalty Score: {result.penalty} (Lower is better, 0.0 means perfect)")
        typer.echo("-" * 60)

        if result.penalty == 0.0 or not result.detail.strip():
            typer.secho("Congratulations! Zero rule violations or penalties found.", fg=typer.colors.GREEN)
            return

        typer.secho(result.detail.strip(), fg=typer.colors.RED)