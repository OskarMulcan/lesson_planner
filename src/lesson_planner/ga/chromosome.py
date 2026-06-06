from uuid import UUID
from dataclasses import dataclass, field

from lesson_planner.models import DayOfWeek

@dataclass
class TimeSlot:
    day: DayOfWeek
    slot_id: UUID


@dataclass
class LessonGene:
    requirement_id: tuple[UUID, UUID]
    teacher_id: UUID
    room_id: UUID
    time_slot: TimeSlot


@dataclass
class ScheduleChromosome:
    lessons: list[LessonGene] = field(default_factory=list)
    generation: int = 0
    _fitness: float | None = field(default=None, repr=False)

    def invalidate_fitness(self):
        self._fitness = None

    @property
    def fitness(self) -> float | None:
        return self._fitness

    @fitness.setter
    def fitness(self, value: float):
        self._fitness = value

