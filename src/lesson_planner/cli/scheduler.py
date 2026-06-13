import logging
from typing import Annotated
import typer

from lesson_planner.logging_setup import configure_logging
from lesson_planner.database import get_session

from lesson_planner.scheduler.schemas import build_scheduling_context
from lesson_planner.scheduler.constraints.base import CompositeConstraint
from lesson_planner.scheduler.constraints.constraints import (
    NoDoubleBookingConstraint,
    LessonFrequencyConstraint,
    PenalizeClassWindowsConstraint,
    PenalizeTeacherWindowsConstraint
)
from lesson_planner.scheduler.ga_engine import GeneticEngine
from lesson_planner.scheduler.persistence import SchedulePersister

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

        typer.echo("Assembling constraints...")
        registry = CompositeConstraint(
            "master_registry",
            NoDoubleBookingConstraint(),
            LessonFrequencyConstraint(),
            PenalizeClassWindowsConstraint(),
            PenalizeTeacherWindowsConstraint(),
        )

        typer.echo(f"Initializing Genetic Engine (Max Generations: {max_generations})...")
        engine = GeneticEngine(
            context=context,
            registry=registry,
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