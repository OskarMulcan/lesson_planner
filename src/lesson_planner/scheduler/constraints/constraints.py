from collections import defaultdict

from .base import Constraint, ConstraintResult
from lesson_planner.scheduler.chromosome import ScheduleChromosome
from lesson_planner.scheduler.scheduler_models import SchedulingContext


class NoDoubleBookingConstraint(Constraint):
    PENALTY = 1000.0

    @property
    def name(self) -> str:
        return "no_double_booking"

    def evaluate(self, schedule: ScheduleChromosome, context: SchedulingContext) -> ConstraintResult:
        seen_teacher: set[tuple] = set()
        seen_class: set[tuple] = set()
        seen_room: set[tuple] = set()
        penalty = 0.0
        violations: list[str] = []

        for lesson in schedule.lessons:
            t_key = (lesson.teacher_id, lesson.day, lesson.slot_id)
            c_key = (lesson.class_id,   lesson.day, lesson.slot_id)
            r_key = (lesson.room_id,    lesson.day, lesson.slot_id)

            if t_key in seen_teacher:
                penalty += self.PENALTY
                violations.append(f"Teacher {lesson.teacher_id} double-booked on {lesson.day} slot {lesson.slot_id}")
            if c_key in seen_class:
                penalty += self.PENALTY
                violations.append(f"Class {lesson.class_id} double-booked on {lesson.day} slot {lesson.slot_id}")
            if r_key in seen_room:
                penalty += self.PENALTY
                violations.append(f"Room {lesson.room_id} double-booked on {lesson.day} slot {lesson.slot_id}")

            seen_teacher.add(t_key)
            seen_class.add(c_key)
            seen_room.add(r_key)

        return ConstraintResult(name=self.name, penalty=penalty, detail=" | ".join(violations))


class TeacherAvailabilityConstraint(Constraint):
    PENALTY = 100.0

    @property
    def name(self) -> str:
        return "teacher_availability"

    def evaluate(self, schedule: ScheduleChromosome, context: SchedulingContext) -> ConstraintResult:
        penalty = 0.0
        violations: list[str] = []

        for lesson in schedule.lessons:
            available = context.teacher_available.get(lesson.teacher_id, frozenset())
            if (lesson.day, lesson.slot_id) not in available:
                penalty += self.PENALTY
                violations.append(
                    f"Teacher {lesson.teacher_id} unavailable on {lesson.day} slot {lesson.slot_id}"
                )

        return ConstraintResult(name=self.name, penalty=penalty, detail=" | ".join(violations))


class LessonFrequencyConstraint(Constraint):
    PENALTY = 1000.0

    @property
    def name(self) -> str:
        return "lesson_frequency"

    def evaluate(self, schedule: ScheduleChromosome, context: SchedulingContext) -> ConstraintResult:
        counts: dict[tuple, int] = defaultdict(int)
        for lesson in schedule.lessons:
            counts[(lesson.class_id, lesson.subject_id)] += 1

        penalty = 0.0
        violations: list[str] = []
        for class_id, subject_requirements in context.required_lessons.items():
            for subject_id, required in subject_requirements.items():
                actual = counts.get((class_id, subject_id), 0)
                diff = abs(actual - required)
                if diff:
                    penalty += diff * self.PENALTY
                    violations.append(
                        f"Class {class_id} subject {subject_id}: expected {required} got {actual}"
                    )

        return ConstraintResult(name=self.name, penalty=penalty, detail=" | ".join(violations))
