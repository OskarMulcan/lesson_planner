from __future__ import annotations

from collections import defaultdict
from random import sample, choice, random, shuffle

from .scheduler_models import SchedulingContext
from .chromosome import ScheduleChromosome, LessonGene
from .constraints.base import CompositeConstraint


class Population:
    def __init__(self, context: SchedulingContext, registry: CompositeConstraint) -> None:
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

    def _build_lesson_queue(self):
        queue = []
        for class_id, subject_requirements in self._context.required_lessons.items():
            for subject_id, count in subject_requirements.items():
                for _ in range(count):
                    queue.append((class_id, subject_id))
        shuffle(queue)
        return queue

    def _generate_chromosome(self) -> ScheduleChromosome:

        TEACHER_MAX_DAILY = 6
        chromosome = ScheduleChromosome()

        teacher_busy: set[tuple] = set()
        class_busy: set[tuple] = set()
        room_busy: set[tuple] = set()
        teacher_daily_count: dict[tuple, int] = defaultdict(int)

        for class_id, subject_id in self._build_lesson_queue():
            teachers = list(self._context.subject_teachers.get(subject_id, []))
            rooms = list(self._context.subject_rooms.get(subject_id, []))
            day_slots = list(self._context.all_day_slots)
            if not teachers or not rooms or not day_slots:
                continue

            shuffle(teachers)
            shuffle(rooms)
            shuffle(day_slots)

            placed = False
            # pass 1: respect daily limit + teacher availability
            # pass 2: ignore availability, keep daily limit
            # pass 3: ignore daily limit too (last resort, avoids only hard collisions)
            for relax_availability, relax_daily in ((False, False), (True, False), (True, True)):
                for teacher_id in teachers:
                    available = self._context.teacher_available.get(teacher_id)
                    for day, slot_id in day_slots:
                        if not relax_availability and available is not None and (day, slot_id) not in available:
                            continue
                        if not relax_daily and teacher_daily_count[(teacher_id, day)] >= TEACHER_MAX_DAILY:
                            continue
                        if (teacher_id, day, slot_id) in teacher_busy:
                            continue
                        if (class_id, day, slot_id) in class_busy:
                            continue
                        for room_id in rooms:
                            if (room_id, day, slot_id) in room_busy:
                                continue
                            chromosome.lessons.append(LessonGene(
                                class_id=class_id,
                                subject_id=subject_id,
                                teacher_id=teacher_id,
                                room_id=room_id,
                                day=day,
                                slot_id=slot_id,
                            ))
                            teacher_busy.add((teacher_id, day, slot_id))
                            class_busy.add((class_id, day, slot_id))
                            room_busy.add((room_id, day, slot_id))
                            teacher_daily_count[(teacher_id, day)] += 1
                            placed = True
                            break
                        if placed:
                            break
                    if placed:
                        break
                if placed:
                    break

            if not placed:
                day, slot_id = choice(day_slots)
                chromosome.lessons.append(LessonGene(
                    class_id=class_id,
                    subject_id=subject_id,
                    teacher_id=choice(teachers),
                    room_id=choice(rooms),
                    day=day,
                    slot_id=slot_id,
                ))

        return chromosome

    def populate(self, population_size: int) -> None:
        self._schedules = [self._generate_chromosome() for _ in range(population_size)]
    '''
    def populate(self, population_size: int) -> None:
        self._schedules = []
        for _ in range(population_size):
            chromosome = ScheduleChromosome()
            for class_id, subject_requirements in self._context.required_lessons.items():
                for subject_id, count in subject_requirements.items():
                    for _ in range(count):
                        gene = self._generate_gene(class_id, subject_id)
                        if gene is not None:
                            chromosome.lessons.append(gene)
            self._schedules.append(chromosome)
    '''
    def evaluate_all(self) -> None:
        for chromosome in self._schedules:
            result = self._registry.evaluate(chromosome, self._context)
            chromosome.fitness = result.penalty

    def selection(self, tournament_size: int) -> ScheduleChromosome:
        candidates = sample(self._schedules, tournament_size)
        return min(candidates, key=lambda s: s.fitness if s.fitness is not None else float("inf"))

    def crossover(self, parent_a: ScheduleChromosome, parent_b: ScheduleChromosome) -> ScheduleChromosome:
        groups_a: dict[tuple, list[LessonGene]] = defaultdict(list)
        groups_b: dict[tuple, list[LessonGene]] = defaultdict(list)
        for lesson in parent_a.lessons:
            groups_a[(lesson.class_id, lesson.subject_id)].append(lesson)
        for lesson in parent_b.lessons:
            groups_b[(lesson.class_id, lesson.subject_id)].append(lesson)

        child_lessons: list[LessonGene] = []
        for key, lessons_a in groups_a.items():
            lessons_b = groups_b.get(key, lessons_a)
            for i, lesson_a in enumerate(lessons_a):
                lesson_b = lessons_b[i] if i < len(lessons_b) else lesson_a
                child_lessons.append(lesson_a if random() < 0.5 else lesson_b)

        return ScheduleChromosome(lessons=child_lessons, generation=parent_a.generation + 1)

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

                # LessonGene is frozen - replace rather than mutate in place
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