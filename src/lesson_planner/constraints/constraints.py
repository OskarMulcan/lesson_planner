from constraints.base import Constraint, ConstraintResult
from ga.chromosome import ScheduleChromosome
from ga.engine import SchedulerContext


class PenalizeWindows(Constraint):
    penalty = 50
    def evaluate(self, schedule: ScheduleChromosome, context: SchedulerContext) -> ConstraintResult:
        pass

class NoDoubleBooking(Constraint):
    penalty = 1000
    def evaluate(self, schedule: ScheduleChromosome, context: SchedulerContext) -> ConstraintResult:
        pass