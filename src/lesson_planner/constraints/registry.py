from ga.engine import SchedulerContext
from .base import Constraint
from ga.chromosome import ScheduleChromosome


class ConstraintRegistry:
    def __init__(self):
        self._constrains: list[Constraint] = []

    def register(self, constraint: Constraint):
        self._constrains.append(constraint)
        return self

    def evaluate_fitness(self, schedule: ScheduleChromosome, context: SchedulerContext) -> tuple[float, dict]:
        total = 0
        results = {}
        for constraint in self._constrains:
            result = constraint.evaluate(schedule, context)
            total += result.penalty
            results[constraint.name] = result
        return total, results