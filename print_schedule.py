"""Run the scheduler and print the resulting plan as a readable grid per class."""
from __future__ import annotations

from collections import defaultdict

from lesson_planner.database import get_session
from lesson_planner.logging_setup import configure_logging
from lesson_planner.models import Class, LessonSlot, Room, Subject, Teacher
from lesson_planner.scheduler.constraints.base import CompositeConstraint
from lesson_planner.scheduler.constraints.constraints import (
    LessonFrequencyConstraint,
    NoDoubleBookingConstraint,
    PenalizeClassWindowsConstraint,
    PenalizeTeacherWindowsConstraint,
    TeacherAvailabilityConstraint,
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
            PenalizeClassWindowsConstraint(),
            PenalizeTeacherWindowsConstraint(),
        )
        engine = GeneticEngine(
            context=context,
            registry=registry,
            population_size=50,
            tournament_size=3,
            mutation_rate=0.05,
            repair_every_n=5,
            max_generations=100,
            fitness_threshold=0.0,
            elite_size=1,
        )
        best = engine.run()
        print(f"\nBest fitness: {best.fitness}, lessons: {len(best.lessons)}\n")

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


if __name__ == "__main__":
    main()