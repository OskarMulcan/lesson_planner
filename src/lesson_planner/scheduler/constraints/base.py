from abc import ABC, abstractmethod
from dataclasses import dataclass

from lesson_planner.scheduler.chromosome import ScheduleChromosome
from lesson_planner.scheduler.schemas import SchedulingContext


@dataclass
class ConstraintResult:
    name: str
    penalty: float
    detail: str = ""


class Constraint(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def evaluate(self, schedule: ScheduleChromosome, context: SchedulingContext) -> ConstraintResult: ...


class CompositeConstraint(Constraint):
    """Is itself a Constraint, but composed of many - can be nested."""

    def __init__(self, name: str, *constraints: Constraint) -> None:
        self._name = name
        self._constraints = list(constraints)

    @property
    def name(self) -> str:
        return self._name

    def evaluate(self, schedule: ScheduleChromosome, context: SchedulingContext) -> ConstraintResult:
        total = 0.0
        details = []
        for constraint in self._constraints:
            result = constraint.evaluate(schedule, context)
            total += result.penalty
            if result.penalty > 0:
                details.append(f"{result.name} [{result.penalty}]: {result.detail}\n")
        return ConstraintResult(
            name=self.name,
            penalty=total,
            detail="\n".join(details),
        )