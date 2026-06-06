from random import choice

from lesson_planner.models import DayOfWeek
from .chromosome import ScheduleChromosome, TimeSlot
from .engine import SchedulerContext


class RepairsOperator:
    def __init__(self, context: SchedulerContext):
        self._context = context

    def _random_timeslot(self) -> TimeSlot:
        return TimeSlot(
            day=choice(list(DayOfWeek)),
            slot_id=choice(list(self._context.lesson_slots.values())).id
        )

    def _repair_teacher_double_booking(self, schedule: ScheduleChromosome) -> None:
        seen: set[tuple] = set()
        for lesson in schedule.lessons:
            key = (lesson.teacher_id, lesson.time_slot.day, lesson.time_slot.slot_id)
            if key in seen:
                req = self._context.requirements[lesson.requirement_id]
                viable = [
                    ts for ts in self._context.teacher_subjects.get(req.subject_id, [])
                    if ts.teacher_id != lesson.teacher_id
                ]
                if viable:
                    lesson.teacher_id = choice(viable).teacher_id
                else:
                    lesson.time_slot = self._random_timeslot()
            else:
                seen.add(key)

    def _repair_room_collision(self, schedule: ScheduleChromosome) -> None:
        seen: set[tuple] = set()
        for lesson in schedule.lessons:
            key = (lesson.room_id, lesson.time_slot.day, lesson.time_slot.slot_id)
            if key in seen:
                free_rooms = [
                    r for r in self._context.rooms.values()
                    if (r.id, lesson.time_slot.day, lesson.time_slot.slot_id) not in seen
                ]
                if free_rooms:
                    lesson.room_id = choice(free_rooms).id
                else:
                    lesson.time_slot = self._random_timeslot()
            seen.add((lesson.room_id, lesson.time_slot.day, lesson.time_slot.slot_id))

    def repair(self, schedule: ScheduleChromosome) -> None:
        self._repair_teacher_double_booking(schedule)
        self._repair_room_collision(schedule)