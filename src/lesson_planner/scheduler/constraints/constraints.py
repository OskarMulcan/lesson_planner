from __future__ import annotations
from typing import TYPE_CHECKING, Any
from collections import defaultdict

from .base import Constraint, ConstraintResult
from ...models import DayOfWeek

if TYPE_CHECKING:
    from ...scheduler.schemas import SchedulingContext
    from ...scheduler.chromosome import ScheduleChromosome


def _slot_positions(context: SchedulingContext) -> dict[Any, int]:
    """Map slot_id -> position-in-day (0-indexed), based on slot order."""
    days = list(DayOfWeek)
    if not context.all_day_slots:
        return {}
    slots_per_day = len(context.all_day_slots) // len(days)
    return {
        slot_id: position
        for position, (_, slot_id) in enumerate(context.all_day_slots[:slots_per_day])
    }


class ConstraintFormatter:
    """Helper to cleanly format DB objects and positions without destroying trace IDs."""
    
    @staticmethod
    def short_id(uid: Any) -> str:
        """Truncates a standard UUID string down to its recognizable 8-char prefix."""
        s = str(uid)
        return s.split("-")[0] if "-" in s else s[:8]

    @staticmethod
    def slot_str(slot_id: Any, positions: dict) -> str:
        """Converts an opaque slot UUID into a human-friendly index string (e.g., 'Slot #2')."""
        pos = positions.get(slot_id)
        if pos is not None:
            return f"Slot #{pos + 1}"
        return f"Slot ({str(slot_id)[:8]})"

    @staticmethod
    def day_str(day: Any) -> str:
        """Returns clean string representation of the day without Enum boilerplate."""
        return day.name if hasattr(day, "name") else str(day)


class NoDoubleBookingConstraint(Constraint):
    PENALTY = 10000.0

    @property
    def name(self) -> str:
        return "no_double_booking"

    def evaluate(self, schedule: ScheduleChromosome, context: SchedulingContext) -> ConstraintResult:
        positions = _slot_positions(context)
        seen_teacher: set[tuple] = set()
        seen_class: set[tuple] = set()
        seen_room: set[tuple] = set()
        penalty = 0.0
        violations: list[str] = []

        for lesson in schedule.lessons:
            t_key = (lesson.teacher_id, lesson.day, lesson.slot_id)
            c_key = (lesson.class_id,   lesson.day, lesson.slot_id)
            r_key = (lesson.room_id,    lesson.day, lesson.slot_id)

            day_lbl = ConstraintFormatter.day_str(lesson.day)
            slot_lbl = ConstraintFormatter.slot_str(lesson.slot_id, positions)

            if t_key in seen_teacher:
                penalty += self.PENALTY
                t_lbl = ConstraintFormatter.short_id(lesson.teacher_id)
                violations.append(f"Teacher [{t_lbl}] double-booked on {day_lbl} at {slot_lbl}")
                
            if c_key in seen_class:
                penalty += self.PENALTY
                c_lbl = ConstraintFormatter.short_id(lesson.class_id)
                violations.append(f"Class [{c_lbl}] double-booked on {day_lbl} at {slot_lbl}")
                
            if r_key in seen_room:
                penalty += self.PENALTY
                r_lbl = ConstraintFormatter.short_id(lesson.room_id)
                violations.append(f"Room [{r_lbl}] double-booked on {day_lbl} at {slot_lbl}")

            seen_teacher.add(t_key)
            seen_class.add(c_key)
            seen_room.add(r_key)

        return ConstraintResult(name=self.name, penalty=penalty, detail=" | ".join(violations))


class TeacherAvailabilityConstraint(Constraint):
    PENALTY = 10000.0

    @property
    def name(self) -> str:
        return "teacher_availability"

    def evaluate(self, schedule: ScheduleChromosome, context: SchedulingContext) -> ConstraintResult:
        positions = _slot_positions(context)
        penalty = 0.0
        violations: list[str] = []

        for lesson in schedule.lessons:
            available = context.teacher_available.get(lesson.teacher_id, frozenset())
            if (lesson.day, lesson.slot_id) not in available:
                penalty += self.PENALTY
                t_lbl = ConstraintFormatter.short_id(lesson.teacher_id)
                day_lbl = ConstraintFormatter.day_str(lesson.day)
                slot_lbl = ConstraintFormatter.slot_str(lesson.slot_id, positions)
                violations.append(f"Teacher [{t_lbl}] unavailable on {day_lbl} at {slot_lbl}")

        return ConstraintResult(name=self.name, penalty=penalty, detail=" | ".join(violations))


class LessonFrequencyConstraint(Constraint):
    PENALTY = 10000.0

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
                    c_lbl = ConstraintFormatter.short_id(class_id)
                    s_lbl = ConstraintFormatter.short_id(subject_id)
                    violations.append(f"Class [{c_lbl}] Subject [{s_lbl}]: expected {required}, got {actual}")

        return ConstraintResult(name=self.name, penalty=penalty, detail=" | ".join(violations))


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
                c_lbl = ConstraintFormatter.short_id(class_id)
                day_lbl = ConstraintFormatter.day_str(day)
                violations.append(f"Class [{c_lbl}] has {gaps} gap slot(s) on {day_lbl}")
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
                t_lbl = ConstraintFormatter.short_id(teacher_id)
                day_lbl = ConstraintFormatter.day_str(day)
                violations.append(f"Teacher [{t_lbl}] has {gaps} gap slot(s) on {day_lbl}")
        return ConstraintResult(name=self.name, penalty=penalty, detail=" | ".join(violations))