from uuid import UUID
from dataclasses import dataclass, field

from lesson_planner.models import DayOfWeek


@dataclass(slots=True, frozen=True)
class LessonGene:
    class_id:   UUID
    subject_id: UUID
    teacher_id: UUID
    room_id:    UUID
    day:        DayOfWeek
    slot_id:    UUID


@dataclass(slots=True)
class ScheduleChromosome:
    lessons: list[LessonGene] = field(default_factory=list)
    generation: int = 0
    fitness: float | None = field(default=None, repr=False, compare=False)
