from __future__ import annotations

from random import choice
from typing import Callable
from dataclasses import replace
from uuid import UUID

from .chromosome import ScheduleChromosome, LessonGene
from .scheduler_models import SchedulingContext
from lesson_planner.models import DayOfWeek


class RepairsOperator:
    def __init__(self, context: SchedulingContext) -> None:
        self._context = context

    def _random_available_slot(self, teacher_id) -> tuple[DayOfWeek, object]:
        available = self._context.teacher_available.get(teacher_id)
        if available:
            return choice(list(available))
        return choice(self._context.all_day_slots)

    def _repair_collisions(
        self,
        lessons: list[LessonGene],
        get_key: Callable[[LessonGene], UUID],
        field_name: str,
        get_alternatives: Callable[[LessonGene, set], list[UUID]],
    ) -> list[LessonGene]:
        seen: set = set()
        result: list[LessonGene] = []

        for lesson in lessons:
            slot_key = (get_key(lesson), lesson.day, lesson.slot_id)

            if slot_key not in seen:
                seen.add(slot_key)
                result.append(lesson)
                continue

            alternatives = get_alternatives(lesson, seen)
            if alternatives:
                new_lesson = replace(lesson, **{field_name: choice(alternatives)})
            else:
                day, slot_id = self._random_available_slot(lesson.teacher_id)
                new_lesson = replace(lesson, day=day, slot_id=slot_id)

            seen.add((get_key(new_lesson), new_lesson.day, new_lesson.slot_id))
            result.append(new_lesson)

        return result

    def repair(self, chromosome: ScheduleChromosome) -> None:
        chromosome.lessons = self._repair_collisions(
            chromosome.lessons,
            get_key=lambda l: l.teacher_id,
            field_name="teacher_id",
            get_alternatives=lambda l, seen: [
                tid for tid in self._context.subject_teachers.get(l.subject_id, [])
                if (tid, l.day, l.slot_id) not in seen
            ],
        )
        chromosome.lessons = self._repair_collisions(
            chromosome.lessons,
            get_key=lambda l: l.room_id,
            field_name="room_id",
            get_alternatives=lambda l, seen: [
                rid for rid in self._context.subject_rooms.get(l.subject_id, [])
                if (rid, l.day, l.slot_id) not in seen
            ],
        )
        chromosome.lessons = self._repair_collisions(
            chromosome.lessons,
            get_key=lambda l: l.class_id,
            field_name="slot_id",
            get_alternatives=lambda l, seen: [],
        )
        chromosome.fitness = None