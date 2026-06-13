from __future__ import annotations

from random import sample, choice, random

from .schemas import SchedulingContext
from .chromosome import ScheduleChromosome, LessonGene
from .constraints import Constraint


class Population:
    def __init__(self, context: SchedulingContext, registry: Constraint) -> None:
        self._context = context
        self._registry = registry
        self._schedules: list[ScheduleChromosome] = []

    @property
    def schedules(self) -> list[ScheduleChromosome]:
        return self._schedules

    @schedules.setter
    def schedules(self, schedules: list[ScheduleChromosome]) -> None:
        self._schedules = schedules

    def _generate_gene(self, class_id, subject_id) -> LessonGene | None:
        teachers = self._context.subject_teachers.get(subject_id, [])
        rooms = self._context.subject_rooms.get(subject_id, [])

        if not teachers or not rooms or not self._context.all_day_slots:
            return None

        day, slot_id = choice(self._context.all_day_slots)

        return LessonGene(
            class_id=class_id,
            subject_id=subject_id,
            teacher_id=choice(teachers),
            room_id=choice(rooms),
            day=day,
            slot_id=slot_id,
        )

    def build_chromosome(self, generation: int = 0) -> ScheduleChromosome:
        """Build a single, freshly-randomised chromosome.

        Every chromosome built this way has the same number of lessons, in
        the same (class_id, subject_id) order, because ``required_lessons``
        and the teacher/room availability per subject are fixed properties
        of the scheduling context - only the randomly chosen
        teacher/room/day/slot per gene differ. This keeps the population
        homogeneous, which ``crossover`` relies on for positional
        alignment, and lets unrepairable chromosomes be swapped out for a
        fresh one of the same "shape" (see ``GeneticEngine``).
        """
        chromosome = ScheduleChromosome(generation=generation)
        for class_id, subject_requirements in self._context.required_lessons.items():
            for subject_id, count in subject_requirements.items():
                for _ in range(count):
                    gene = self._generate_gene(class_id, subject_id)
                    if gene is not None:
                        chromosome.lessons.append(gene)
        return chromosome

    def populate(self, population_size: int) -> None:
        self._schedules = [self.build_chromosome() for _ in range(population_size)]

    def evaluate_all(self) -> None:
        for chromosome in self._schedules:
            result = self._registry.evaluate(chromosome, self._context)
            chromosome.fitness = result.penalty

    def selection(self, tournament_size: int) -> ScheduleChromosome:
        candidates = sample(self._schedules, tournament_size)
        return min(candidates, key=lambda s: s.fitness if s.fitness is not None else float("inf"))

    def crossover(self, parent_a: ScheduleChromosome, parent_b: ScheduleChromosome) -> ScheduleChromosome:
        """Single-point crossover - split lessons list at a random index.

        Both parents originate from ``build_chromosome`` (directly, or via
        repair which preserves length/order, or via a previous crossover),
        so they always have the same number of lessons in the same
        (class_id, subject_id) order; slicing at any index keeps that
        alignment intact in the child.
        """
        cut = len(parent_a.lessons) // 2
        child = ScheduleChromosome(
            lessons=parent_a.lessons[:cut] + parent_b.lessons[cut:],
            generation=max(parent_a.generation, parent_b.generation) + 1,
        )
        return child

    def mutate(self, chromosome: ScheduleChromosome, mutation_rate: float) -> None:
        new_lessons: list[LessonGene] = []
        for lesson in chromosome.lessons:
            if random() < mutation_rate:
                day, slot_id = choice(self._context.all_day_slots)

                new_teacher = (
                    choice(self._context.subject_teachers[lesson.subject_id])
                    if random() < 0.3 and self._context.subject_teachers.get(lesson.subject_id)
                    else lesson.teacher_id
                )
                new_room = (
                    choice(self._context.subject_rooms[lesson.subject_id])
                    if random() < 0.3 and self._context.subject_rooms.get(lesson.subject_id)
                    else lesson.room_id
                )

                new_lessons.append(LessonGene(
                    class_id=lesson.class_id,
                    subject_id=lesson.subject_id,
                    teacher_id=new_teacher,
                    room_id=new_room,
                    day=day,
                    slot_id=slot_id,
                ))
            else:
                new_lessons.append(lesson)

        chromosome.lessons = new_lessons
        chromosome.fitness = None