"""Ad-hoc script to run the genetic scheduler against the current database."""

from __future__ import annotations

from lesson_planner.database import get_session
from lesson_planner.logging_setup import configure_logging
from lesson_planner.scheduler.constraints.base import CompositeConstraint
from lesson_planner.scheduler.constraints.constraints import (
    LessonFrequencyConstraint,
    NoDoubleBookingConstraint,
    TeacherAvailabilityConstraint,
)
from lesson_planner.scheduler.ga_engine import GeneticEngine
from lesson_planner.scheduler.scheduler_models import build_scheduling_context


def main() -> None:
    configure_logging()

    with get_session() as session:
        context = build_scheduling_context(session)

        if not context.required_lessons:
            raise SystemExit(
                "Brak wymagań planowania w bazie. Zaimportuj dane (np. requirements, classes, teachers)."
            )

        registry = CompositeConstraint(
            "default",
            NoDoubleBookingConstraint(),
            TeacherAvailabilityConstraint(),
            LessonFrequencyConstraint(),
        )

        engine = GeneticEngine(
            context=context,
            registry=registry,
            population_size=50,
            tournament_size=3,
            mutation_rate=0.05,
            repair_every_n=5,
            max_generations=100,
            fitness_threshold=0.0,
            elite_size=1,
        )

        best = engine.run()
        print(f"Best fitness: {best.fitness}, lessons: {len(best.lessons)}")


if __name__ == "__main__":
    main()
