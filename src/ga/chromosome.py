from dataclasses import dataclass, field

DAYS = 5
LESSONS_PER_DAY = 10

@dataclass
class TimeSlot:
    day: int
    slot: int

    def to_int(self) -> int:
        return (self.day - 1) * LESSONS_PER_DAY + self.slot

    @staticmethod
    def from_int(n: int) -> 'TimeSlot':
        return TimeSlot(day= n // LESSONS_PER_DAY + 1, slot=n % LESSONS_PER_DAY + 1)

    def __hash__(self):
        return hash(self.to_int())


@dataclass
class ScheduledLesson:
    requirement_id: int
    room_id: int
    time_slot: TimeSlot


@dataclass
class Schedule:
    lessons: list[ScheduledLesson] = field(default_factory=list)
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


