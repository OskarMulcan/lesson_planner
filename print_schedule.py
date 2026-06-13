"""Run the scheduler and print the resulting plan as a readable grid per class."""
from __future__ import annotations

from collections import defaultdict

from lesson_planner.database import get_session
from lesson_planner.logging_setup import configure_logging
from lesson_planner.models import Class, LessonSlot, Room, Subject, Teacher
from lesson_planner.scheduler.constraints.base import CompositeConstraint
from lesson_planner.scheduler.constraints.constraints import (
    LessonFrequencyConstraint,
    MaxLessonsPerDayPerClassConstraint,
    NoDoubleBookingConstraint,
    PenalizeClassWindowsConstraint,
    PenalizeLateSlotsConstraint,
    PenalizeTeacherWindowsConstraint,
    TeacherAvailabilityConstraint,
    TeacherMaxDailyLessonsConstraint,
)
from lesson_planner.scheduler.ga_engine import GeneticEngine
from lesson_planner.scheduler.scheduler_models import build_scheduling_context


DAY_ORDER = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]


def main() -> None:
    configure_logging()
    with get_session() as session:
        context = build_scheduling_context(session)

        registry = CompositeConstraint(
            "default",
            NoDoubleBookingConstraint(),
            TeacherAvailabilityConstraint(),
            LessonFrequencyConstraint(),
            MaxLessonsPerDayPerClassConstraint(),
            TeacherMaxDailyLessonsConstraint(),
            PenalizeClassWindowsConstraint(),
            PenalizeTeacherWindowsConstraint(),
            PenalizeLateSlotsConstraint(),
        )
        engine = GeneticEngine(
            context=context,
            registry=registry,
            population_size=100,
            tournament_size=3,
            mutation_rate=0.07,
            repair_every_n=5,
            max_generations=2000,
            fitness_threshold=0.0,
            elite_size=5,
        )

        best = engine.run()

        result = registry.evaluate(best, context)
        print(f"=== Violations (total penalty: {result.penalty}) ===")

        # id -> display name lookups
        classes = {c.id: c.name for c in session.query(Class).all()}
        subjects = {s.id: s.code for s in session.query(Subject).all()}
        teachers = {t.id: f"{t.first_name[0]}.{t.last_name}" for t in session.query(Teacher).all()}
        rooms = {r.id: r.number for r in session.query(Room).all()}
        slots = {
            sl.id: (sl.slot_number, sl.start_time.strftime("%H:%M"))
            for sl in session.query(LessonSlot).all()
        }

        # group lessons per class
        by_class: dict = defaultdict(list)
        for lesson in best.lessons:
            by_class[lesson.class_id].append(lesson)

        for class_id, lessons in by_class.items():
            print(f"=== Class {classes.get(class_id, class_id)} ===")

            # grid[slot_number][day] = cell text
            grid: dict = defaultdict(dict)
            for lesson in lessons:
                slot_number, start_time = slots[lesson.slot_id]
                cell = (
                    f"{subjects[lesson.subject_id]} "
                    f"({teachers[lesson.teacher_id]}, room {rooms[lesson.room_id]})"
                )
                grid[slot_number][lesson.day.name] = (start_time, cell)

            for slot_number in sorted(grid):
                row = grid[slot_number]
                start_time = next(iter(row.values()))[0]
                print(f"  Slot {slot_number} ({start_time})")
                for day in DAY_ORDER:
                    if day in row:
                        print(f"    {day:<10} {row[day][1]}")
            print()

        id_to_name = {}
        id_to_name.update({k: f"class {v}" for k, v in classes.items()})
        id_to_name.update({k: f"subject {v}" for k, v in subjects.items()})
        id_to_name.update({k: f"teacher {v}" for k, v in teachers.items()})
        id_to_name.update({k: f"room {v}" for k, v in rooms.items()})

        def readable(text: str) -> str:
            for uuid_obj, name in id_to_name.items():
                text = text.replace(str(uuid_obj), name)
            return text

        result = registry.evaluate(best, context)
        print(f"=== Violations (total penalty: {result.penalty}) ===")
        print(readable(result.detail) or "(none)")
        print()

if __name__ == "__main__":
    main()