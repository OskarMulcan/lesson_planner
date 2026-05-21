from abc import abstractmethod, ABC
from dataclasses import dataclass, field

from ga.chromosome import Schedule
from ga.engine import SchedulerContext


@dataclass
class ConstraintResult:
    penalty: float
    violations: list[str] = field(default_factory=list)

@dataclass
class Constraint(ABC):
    penalty: float

    @property
    def name(self):
        return self.__class__.__name__

    @abstractmethod
    def evaluate(self, schedule: Schedule, context: SchedulerContext) -> ConstraintResult:
        pass
