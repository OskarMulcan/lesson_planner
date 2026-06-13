from collections import defaultdict

from .base import Constraint, ConstraintResult
from lesson_planner.scheduler.chromosome import ScheduleChromosome
from lesson_planner.scheduler.scheduler_models import SchedulingContext
from lesson_planner.models import DayOfWeek


class NoDoubleBookingConstraint(Constraint):
    PENALTY = 100000.0

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
    PENALTY = 200.0

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
    PENALTY = 100000.0

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

def _slot_positions(context: SchedulingContext) -> dict:
    """Map slot_id -> position-in-day (0-indexed), based on slot order."""
    days = list(DayOfWeek)
    slots_per_day = len(context.all_day_slots) // len(days)
    return {
        slot_id: position
        for position, (_, slot_id) in enumerate(context.all_day_slots[:slots_per_day])
    }


class PenalizeClassWindowsConstraint(Constraint):
    PENALTY = 100.0

    @property
    def name(self) -> str:
        return "class_windows"

    def evaluate(self, schedule: ScheduleChromosome, context: SchedulingContext) -> ConstraintResult:
        positions = _slot_positions(context)
        by_day: dict[tuple, list[int]] = defaultdict(list)
        for lesson in schedule.lessons:
            by_day[(lesson.class_id, lesson.day)].append(positions[lesson.slot_id])

        penalty = 0.0
        violations: list[str] = []
        for (class_id, day), slots in by_day.items():
            slots.sort()
            gaps = sum(b - a - 1 for a, b in zip(slots, slots[1:]) if b - a > 1)
            if gaps:
                penalty += gaps * self.PENALTY
                violations.append(f"Class {class_id} has {gaps} gap slot(s) on {day}")
        return ConstraintResult(name=self.name, penalty=penalty, detail=" | ".join(violations))


class PenalizeTeacherWindowsConstraint(Constraint):
    PENALTY = 50.0

    @property
    def name(self) -> str:
        return "teacher_windows"

    def evaluate(self, schedule: ScheduleChromosome, context: SchedulingContext) -> ConstraintResult:
        positions = _slot_positions(context)
        by_day: dict[tuple, list[int]] = defaultdict(list)
        for lesson in schedule.lessons:
            by_day[(lesson.teacher_id, lesson.day)].append(positions[lesson.slot_id])

        penalty = 0.0
        violations: list[str] = []
        for (teacher_id, day), slots in by_day.items():
            slots.sort()
            gaps = sum(b - a - 1 for a, b in zip(slots, slots[1:]) if b - a > 1)
            if gaps:
                penalty += gaps * self.PENALTY
                violations.append(f"Teacher {teacher_id} has {gaps} gap slot(s) on {day}")
        return ConstraintResult(name=self.name, penalty=penalty, detail=" | ".join(violations))

class MaxLessonsPerDayPerClassConstraint(Constraint):
    PENALTY = 1000.0
    MAX_PER_DAY = 7

    @property
    def name(self) -> str:
        return "max_lessons_per_day_per_class"

    def evaluate(self, schedule: ScheduleChromosome, context: SchedulingContext) -> ConstraintResult:
        counts: dict[tuple, int] = defaultdict(int)
        for lesson in schedule.lessons:
            counts[(lesson.class_id, lesson.day)] += 1

        penalty = 0.0
        violations: list[str] = []
        for (class_id, day), count in counts.items():
            over = count - self.MAX_PER_DAY
            if over > 0:
                penalty += over * self.PENALTY
                violations.append(f"Class {class_id} has {count} lessons on {day} (max {self.MAX_PER_DAY})")
        return ConstraintResult(name=self.name, penalty=penalty, detail=" | ".join(violations))


class TeacherMaxDailyLessonsConstraint(Constraint):
    PENALTY = 10000.0
    MAX_PER_DAY = 6

    @property
    def name(self) -> str:
        return "teacher_max_daily_lessons"

    def evaluate(self, schedule: ScheduleChromosome, context: SchedulingContext) -> ConstraintResult:
        counts: dict[tuple, int] = defaultdict(int)
        for lesson in schedule.lessons:
            counts[(lesson.teacher_id, lesson.day)] += 1

        penalty = 0.0
        violations: list[str] = []
        for (teacher_id, day), count in counts.items():
            over = count - self.MAX_PER_DAY
            if over > 0:
                penalty += over * self.PENALTY
                violations.append(f"Teacher {teacher_id} has {count} lessons on {day} (max {self.MAX_PER_DAY})")
        return ConstraintResult(name=self.name, penalty=penalty, detail=" | ".join(violations))

class PenalizeLateSlotsConstraint(Constraint):
    BASE_PENALTY = 10.0
    MULTIPLIER = 2.0
    THRESHOLD = 5

    @property
    def name(self) -> str:
        return "late_slots"

    def evaluate(self, schedule: ScheduleChromosome, context: SchedulingContext) -> ConstraintResult:
        positions = _slot_positions(context)
        penalty = 0.0
        violations: list[str] = []
        for lesson in schedule.lessons:
            position = positions[lesson.slot_id]
            over = position - self.THRESHOLD
            if over >= 0:
                lesson_penalty = self.BASE_PENALTY * (self.MULTIPLIER ** (over + 1))
                penalty += lesson_penalty
                violations.append(
                    f"Class {lesson.class_id} subject {lesson.subject_id} "
                    f"on {lesson.day} slot-position {position} (+{lesson_penalty})"
                )
        return ConstraintResult(name=self.name, penalty=penalty, detail=" | ".join(violations))