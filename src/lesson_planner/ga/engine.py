from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass

from constraints.registry import ConstraintRegistry
from lesson_planner.models import (
    GradeLevel,
    GradeSubjectRequirement,
    LessonSlot,
    Room,
    Subject,
    Teacher,
    TeacherSubject,
)

from .chromosome import ScheduleChromosome


@dataclass
class SchedulerContext:
    requirements: dict[tuple[uuid.UUID, uuid.UUID], GradeSubjectRequirement]
    teachers: dict[uuid.UUID, Teacher]
    rooms: dict[uuid.UUID, Room]
    grade_levels: dict[uuid.UUID, GradeLevel]
    subjects: dict[uuid.UUID, Subject]
    lesson_slots: dict[uuid.UUID, LessonSlot]
    teacher_subjects: dict[uuid.UUID, list[TeacherSubject]]

    @classmethod
    def load(cls, session) -> SchedulerContext:
        ts_map = defaultdict(list)
        for ts in session.query(TeacherSubject).all():
            ts_map[ts.subject_id].append(ts)

        return cls(
            requirements={(r.grade_level_id, r.subject_id): r for r in session.query(GradeSubjectRequirement).all()},
            teachers={t.id: t for t in session.query(Teacher).all()},
            rooms={r.id: r for r in session.query(Room).all()},
            grade_levels={g.id: g for g in session.query(GradeLevel).all()},
            subjects={s.id: s for s in session.query(Subject).all()},
            lesson_slots={ls.id: ls for ls in session.query(LessonSlot).all()},
            teacher_subjects=dict(ts_map),
        )


class GeneticEngine:
    def __init__(
        self,
        context: SchedulerContext,
        registry: ConstraintRegistry,
        population_size: int,
        tournament_size: int,
        mutation_rate: float,
        repair_every_n: int,
        max_generations: int,
        fitness_threshold: float,
        elite_size: int = 1,
    ):
        from .population import Population
        from .repairs import RepairsOperator

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

    def run(self) -> ScheduleChromosome:
        self._population.populate(self._population_size)
        self._population.set_population_fitness()

        for chromosome in self._population.schedules:
            self._repair.repair(chromosome)
        self._population.set_population_fitness()

        for generation in range(self._max_generations):
            best = min(self._population.schedules, key=lambda s: s.fitness)
            print(f"Generation {generation}, best fitness: {best.fitness}")

            if best.fitness <= self._fitness_threshold:
                break

            elites = sorted(self._population.schedules, key=lambda s: s.fitness)[:self._elite_size]
            new_population = list(elites)

            while len(new_population) < self._population_size:
                parent_a = self._population.selection(self._tournament_size)
                parent_b = self._population.selection(self._tournament_size)
                child = self._population.crossover(parent_a, parent_b)
                self._population.mutate(child, self._mutation_rate)
                new_population.append(child)

            self._population.schedules = new_population
            self._population.set_population_fitness()

            if generation % self._repair_every_n == 0:
                for chromosome in self._population.schedules:
                    self._repair.repair(chromosome)
                self._population.set_population_fitness()

        return min(self._population.schedules, key=lambda s: s.fitness)