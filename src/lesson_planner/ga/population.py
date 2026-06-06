from random import sample, choice, random

from constraints.registry import ConstraintRegistry
from .engine import SchedulerContext
from .chromosome import ScheduleChromosome, LessonGene, TimeSlot
from ..models import DayOfWeek


class Population:
    def __init__(self, context: SchedulerContext, constraint_registry: ConstraintRegistry):
        self._context = context
        self._schedules = []
        self._constraint_registry = constraint_registry

    @property
    def schedules(self):
        return self._schedules

    @schedules.setter
    def schedules(self, schedules: list[ScheduleChromosome]) -> None:
        self._schedules = schedules

    def populate(self, population_size: int) -> list[ScheduleChromosome]:
        schedule_list: list[ScheduleChromosome] = []
        for i in range(population_size):
            schedule = ScheduleChromosome()
            for req in self._context.requirements.values():
                for j in range(req.lessons_per_week):
                    room_id = choice(list(self._context.rooms.values())).id
                    teacher_id = choice(self._context.teacher_subjects[req.subject_id]).teacher_id
                    slot = TimeSlot(
                        day=choice(list(DayOfWeek)),
                        slot_id=choice(list(self._context.lesson_slots.values())).id
                    )
                    scheduled_lesson = LessonGene(requirement_id=(req.grade_level_id, req.subject_id), room_id=room_id, teacher_id=teacher_id, time_slot=slot)
                    schedule.lessons.append(scheduled_lesson)
            schedule_list.append(schedule)
        self._schedules = schedule_list
        return self._schedules

    def set_population_fitness(self) -> None:
        for schedule in self._schedules:
            fitness, _ = self._constraint_registry.evaluate_fitness(schedule, self._context)
            schedule.fitness = fitness

    def selection(self, tournament_size: int) -> ScheduleChromosome:
        candidates = sample(self._schedules, tournament_size)
        return min(candidates, key=lambda s: s.fitness)

    def crossover(self, parent_a: ScheduleChromosome, parent_b: ScheduleChromosome) -> ScheduleChromosome:
        child = ScheduleChromosome()
        lessons_b = {lesson.requirement_id: lesson for lesson in parent_b.lessons}
        for lesson in parent_a.lessons:
            if random() > 0.5:
                child.lessons.append(lesson)
            else:
                child.lessons.append(lessons_b[lesson.requirement_id])
        return child

    def mutate(self, schedule: ScheduleChromosome, mutation_rate: float) -> None:
        for lesson in schedule.lessons:
            if random() < mutation_rate:
                lesson.room_id = choice(list(self._context.rooms.values())).id
                lesson.time_slot = TimeSlot(
                    day=choice(list(DayOfWeek)),
                    slot_id=choice(list(self._context.lesson_slots.values())).id
                )
