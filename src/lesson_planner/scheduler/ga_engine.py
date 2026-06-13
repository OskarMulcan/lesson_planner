from __future__ import annotations

import logging
from typing import Optional

from .schemas import SchedulingContext
from .chromosome import ScheduleChromosome
from .constraints import Constraint
from .population import Population
from .repairs import RepairsOperator

logger = logging.getLogger(__name__)


class GeneticEngine:
    def __init__(
        self,
        context: SchedulingContext,
        registry: Constraint,
        population_size: int,
        tournament_size: int,
        mutation_rate: float,
        repair_every_n: int,
        max_generations: int,
        fitness_threshold: float,
        elite_size: int = 1,
        final_repair_attempts: int = 25,
        final_candidates: int = 5,
    ) -> None:
        self._context = context
        self._registry = registry
        self._population = Population(context, registry)
        self._repair = RepairsOperator(context)
        self._population_size = population_size
        self._tournament_size = tournament_size
        self._mutation_rate = mutation_rate
        self._repair_every_n = repair_every_n
        self._max_generations = max_generations
        self._fitness_threshold = fitness_threshold
        self._elite_size = elite_size
        self._final_repair_attempts = final_repair_attempts
        self._final_candidates = final_candidates

    def _best(self) -> ScheduleChromosome:
        return min(
            self._population.schedules,
            key=lambda s: s.fitness if s.fitness is not None else float("inf"),
        )

    def _sort_key(self, s: ScheduleChromosome) -> float:
        return s.fitness if s.fitness is not None else float("inf")

    def _snapshot(self, chromosome: ScheduleChromosome) -> ScheduleChromosome:
        """A shallow copy that is safe to repair/evaluate without mutating
        ``chromosome``, which may still be referenced from the running
        population (e.g. as an elite)."""
        return ScheduleChromosome(
            lessons=list(chromosome.lessons),
            generation=chromosome.generation,
            fitness=chromosome.fitness,
        )

    def _repair_population(self, generation: int) -> None:
        """Repair every chromosome in the population in place.

        A chromosome that can't be fully repaired (``repair`` returns
        ``False``, meaning at least one lesson has no valid placement left)
        is discarded and replaced with a freshly generated chromosome of the
        same shape, so the population stays at full size and remains
        homogeneous for ``crossover``.
        """
        schedules = self._population.schedules
        for i, chromosome in enumerate(schedules):
            if not self._repair.repair(chromosome):
                schedules[i] = self._population.build_chromosome(generation=generation)

    def _finalize(self, absolute_best: ScheduleChromosome) -> Optional[ScheduleChromosome]:
        """Best-effort attempt to turn a candidate into a schedule that
        satisfies every hard DB constraint.

        The overall best chromosome seen across the run, plus the top
        candidates of the final population, are each given several repair
        attempts. ``repair``'s search is randomised, so different attempts
        explore different lesson orderings and slot/teacher/room choices -
        the first attempt that fully places every required lesson wins.

        Returns ``None`` if none of the attempts succeed: no schedule
        satisfying the hard constraints could be found for this run.
        """
        candidates = [absolute_best] + sorted(
            self._population.schedules, key=self._sort_key
        )[:self._final_candidates]

        for candidate in candidates:
            snapshot = self._snapshot(candidate)
            for _ in range(self._final_repair_attempts):
                if self._repair.repair(snapshot):
                    snapshot.fitness = self._registry.evaluate(snapshot, self._context).penalty
                    return snapshot

        return None

    def run(self) -> Optional[ScheduleChromosome]:
        """Run the genetic search.

        Returns the best schedule found that satisfies every hard database
        constraint (no class/teacher/room double-booked in the same
        day+slot), or ``None`` if no such schedule could be found.
        """

        self._population.populate(self._population_size)
        self._population.evaluate_all()

        absolute_best = self._snapshot(self._best())

        for generation in range(self._max_generations):
            best = self._best()
            print(f"Generation {generation}, best fitness: {best.fitness}")

            if best.fitness is not None and (
                absolute_best.fitness is None or best.fitness < absolute_best.fitness
            ):
                absolute_best = self._snapshot(best)

            if best.fitness is not None and best.fitness <= self._fitness_threshold:
                break

            elites = sorted(self._population.schedules, key=self._sort_key)[:self._elite_size]
            new_population: list[ScheduleChromosome] = list(elites)

            while len(new_population) < self._population_size:
                parent_a = self._population.selection(self._tournament_size)
                parent_b = self._population.selection(self._tournament_size)
                child = self._population.crossover(parent_a, parent_b)
                self._population.mutate(child, self._mutation_rate)
                new_population.append(child)

            self._population.schedules = new_population
            self._population.evaluate_all()

            if generation % self._repair_every_n == 0:
                self._repair_population(generation)
                self._population.evaluate_all()

        final_schedule = self._finalize(absolute_best)
        if final_schedule is None:
            logger.warning(
                "Genetic search produced no schedule satisfying the hard "
                "database constraints after %d generation(s) and %d final "
                "repair attempt(s) across %d candidate(s).",
                self._max_generations,
                self._final_repair_attempts,
                self._final_candidates + 1,
            )

        return final_schedule