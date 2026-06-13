from __future__ import annotations

from .schemas import SchedulingContext
from .chromosome import ScheduleChromosome
from .constraints import Constraint
from .population import Population
from .repairs import RepairsOperator


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

    def _best(self) -> ScheduleChromosome:
        return min(
            self._population.schedules,
            key=lambda s: s.fitness if s.fitness is not None else float("inf"),
        )

    def _sort_key(self, s: ScheduleChromosome) -> float:
        return s.fitness if s.fitness is not None else float("inf")

    def run(self) -> ScheduleChromosome:
        self._population.populate(self._population_size)
        self._population.evaluate_all()

        for generation in range(self._max_generations):
            best = self._best()
            print(f"Generation {generation}, best fitness: {best.fitness}")

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
                for chromosome in self._population.schedules:
                    self._repair.repair(chromosome)
                self._population.evaluate_all()

        return self._best()