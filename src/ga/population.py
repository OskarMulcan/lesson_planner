from random import sample, choice, random

from constraints.registry import ConstraintRegistry
from .engine import SchedulerContext
from .chromosome import DAYS, LESSONS_PER_DAY, Schedule, ScheduledLesson, TimeSlot



class Population:
    def __init__(self, context: SchedulerContext):
        self._context = context
        self._schedules = []
        self._constraint_registry = ConstraintRegistry()

    @property
    def schedules(self):
        return self._schedules

    @schedules.setter
    def schedules(self, schedules: list[Schedule]) -> None:
        self._schedules = schedules

    def populate(self, population_size: int) -> list[Schedule]:
        schedule_list: list[Schedule] = []
        for i in range(population_size):
            schedule = Schedule()
            for req in self._context.requirements.values():
                for j in range(req.lessons_per_week):
                    room_id = choice(list(self._context.rooms.values())).id
                    slot_num = choice(range(1, DAYS*LESSONS_PER_DAY + 1))
                    slot = TimeSlot.from_int(slot_num)
                    scheduled_lesson = ScheduledLesson(requirement_id=req.id, room_id=room_id, time_slot=slot)
                    schedule.lessons.append(scheduled_lesson)
            schedule_list.append(schedule)
        self._schedules = schedule_list
        return self._schedules

    def set_population_fitness(self) -> None:
        for schedule in self._schedules:
            fitness, _ = self._constraint_registry.evaluate_fitness(schedule, self._context)
            schedule.fitness = fitness

    def selection(self, tournament_size: int) -> Schedule:
        candidates = sample(self._schedules, tournament_size)
        return min(candidates, key=lambda s: s.fitness)

    def crossover(self, parent_a: Schedule, parent_b: Schedule) -> Schedule:
        child = Schedule()
        lessons_b = {l.requirement_id: l for l in parent_b.lessons}
        for lesson in parent_a.lessons:
            if random() > 0.5:
                child.lessons.append(lesson)
            else:
                child.lessons.append(lessons_b[lesson.requirement_id])
        return child

    def mutate(self, schedule: Schedule, mutation_rate: float) -> None:
        for lesson in schedule.lessons:
            if random() < mutation_rate:
                lesson.room_id = choice(list(self._context.rooms.values())).id
                lesson.time_slot = TimeSlot.from_int(
                    choice(range(1, DAYS * LESSONS_PER_DAY + 1))
                )

