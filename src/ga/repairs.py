from random import choice

from ga.chromosome import Schedule, TimeSlot, DAYS, LESSONS_PER_DAY
from ga.engine import SchedulerContext


class RepairsOperator:
    def __init__(self, context: SchedulerContext):
        self._context = context

    def _repair_teacher_double_booking(self, schedule: Schedule) -> None:
        seen: dict[tuple, int] = {}
        for lesson in schedule.lessons:
            req = self._context.requirements[lesson.requirement_id]
            key = (req.teacher_id, lesson.time_slot.day, lesson.time_slot.slot)
            if key in seen:
                viable = [
                    ts for ts in self._context.teacher_subjects.values()
                    if ts.subject_id == req.subject_id and ts.teacher_id != req.teacher_id
                ]
                if viable:
                    lesson.requirement_id = next(
                        r.id for r in self._context.requirements.values()
                        if r.teacher_id == viable[0].teacher_id and r.subject_id == req.subject_id
                    )
                else:
                    lesson.time_slot = TimeSlot.from_int(
                        choice(range(1, DAYS * LESSONS_PER_DAY + 1))
                    )
            else:
                seen[key] = lesson.requirement_id

    def _repair_room_collision(self, schedule: Schedule) -> None:
        seen: set[tuple] = set()
        for lesson in schedule.lessons:
            key = (lesson.room_id, lesson.time_slot.day, lesson.time_slot.slot)
            if key in seen:
                free_rooms = [
                    r for r in self._context.rooms.values()
                    if (r.id, lesson.time_slot.day, lesson.time_slot.slot) not in seen
                ]
                if free_rooms:
                    lesson.room_id = choice(free_rooms).id
                else:
                    lesson.time_slot = TimeSlot.from_int(
                        choice(range(1, DAYS * LESSONS_PER_DAY + 1))
                    )
            seen.add((lesson.room_id, lesson.time_slot.day, lesson.time_slot.slot))

    def repair(self, schedule: Schedule) -> None:
        self._repair_teacher_double_booking(schedule)
        self._repair_room_collision(schedule)
