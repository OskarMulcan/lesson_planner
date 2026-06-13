from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from random import choice, shuffle
from typing import Optional
from uuid import UUID

from .chromosome import LessonGene, ScheduleChromosome
from .schemas import SchedulingContext
from lesson_planner.models import DayOfWeek

SlotKey = tuple[DayOfWeek, UUID]


class RepairsOperator:
    """Repairs a chromosome so that it satisfies the hard uniqueness
    constraints enforced by the database:

      * ``uq_schedule_class_day_slot``   - a class can't be in two places
        at once.
      * ``uq_schedule_teacher_day_slot`` - a teacher can't teach two
        lessons at once.
      * ``uq_schedule_room_day_slot``    - a room can't host two lessons
        at once.

    Repair is a constructive, exhaustive-search heuristic. Lessons are
    processed in "most constrained first" order (subjects with the fewest
    eligible teacher/room combinations go first, with a random tie-break),
    and for each lesson every (day, slot) is examined - together with
    every eligible teacher and room for that subject - until a combination
    free of the three constraints above is found.

    A single ``repair`` call either places *every* lesson validly (returns
    ``True``) or leaves the chromosome completely untouched and returns
    ``False``. Because the search order is randomised, retrying ``repair``
    on the same chromosome can succeed even if a previous attempt failed -
    callers that want a strong "is this even achievable" signal should
    retry a number of times (and across a few candidate chromosomes) before
    concluding the schedule is unachievable. See ``feasibility_report`` for
    a cheap upfront sanity check.
    """

    def __init__(self, context: SchedulingContext) -> None:
        self._context = context

    def repair(self, chromosome: ScheduleChromosome) -> bool:
        lessons = chromosome.lessons
        n = len(lessons)

        if n == 0:
            chromosome.fitness = None
            return True

        processing_order = list(range(n))
        shuffle(processing_order)
        processing_order.sort(key=lambda i: self._flexibility(lessons[i]))

        seen_teachers: set[tuple[UUID, DayOfWeek, UUID]] = set()
        seen_rooms: set[tuple[UUID, DayOfWeek, UUID]] = set()
        seen_classes: set[tuple[UUID, DayOfWeek, UUID]] = set()
        result: list[Optional[LessonGene]] = [None] * n

        all_slots = list(self._context.all_day_slots)

        for idx in processing_order:
            placed = self._place(lessons[idx], all_slots, seen_teachers, seen_rooms, seen_classes)
            if placed is None:
                chromosome.fitness = None
                return False

            seen_teachers.add((placed.teacher_id, placed.day, placed.slot_id))
            seen_rooms.add((placed.room_id, placed.day, placed.slot_id))
            seen_classes.add((placed.class_id, placed.day, placed.slot_id))
            result[idx] = placed

        chromosome.lessons = result  # type: ignore[assignment]
        chromosome.fitness = None
        return True

    def _flexibility(self, lesson: LessonGene) -> int:
        """Rough measure of how many valid (teacher, room) combinations
        exist for this lesson's subject - lower means more constrained and
        should be placed first."""
        teachers = len(self._context.subject_teachers.get(lesson.subject_id, ()))
        rooms = len(self._context.subject_rooms.get(lesson.subject_id, ()))
        return teachers * rooms

    def _place(
        self,
        lesson: LessonGene,
        all_slots: list[SlotKey],
        seen_teachers: set[tuple[UUID, DayOfWeek, UUID]],
        seen_rooms: set[tuple[UUID, DayOfWeek, UUID]],
        seen_classes: set[tuple[UUID, DayOfWeek, UUID]],
    ) -> Optional[LessonGene]:
        """Find a (teacher, room, day, slot) for ``lesson`` that doesn't
        collide with anything already placed (tracked via the ``seen_*``
        sets). Returns ``None`` if no such combination exists - i.e. every
        (day, slot) either clashes for this class, or has no free eligible
        teacher, or has no free eligible room.
        """
        teachers = self._context.subject_teachers.get(lesson.subject_id, [])
        rooms = self._context.subject_rooms.get(lesson.subject_id, [])

        if not teachers or not rooms or not all_slots:
            return None

        if all([
            lesson.teacher_id in teachers,
            lesson.room_id in rooms,
            (lesson.teacher_id, lesson.day, lesson.slot_id) not in seen_teachers,
            (lesson.room_id, lesson.day, lesson.slot_id) not in seen_rooms,
            (lesson.class_id, lesson.day, lesson.slot_id) not in seen_classes,
        ]):
            return lesson

        slots = list(all_slots)
        shuffle(slots)

        for day, slot_id in slots:
            if (lesson.class_id, day, slot_id) in seen_classes:
                continue

            free_teachers = [t for t in teachers if (t, day, slot_id) not in seen_teachers]
            if not free_teachers:
                continue

            free_rooms = [r for r in rooms if (r, day, slot_id) not in seen_rooms]
            if not free_rooms:
                continue

            return replace(
                lesson,
                teacher_id=choice(free_teachers),
                room_id=choice(free_rooms),
                day=day,
                slot_id=slot_id,
            )

        return None
