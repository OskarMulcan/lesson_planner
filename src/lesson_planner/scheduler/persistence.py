from uuid import UUID
from sqlalchemy.orm import Session

from lesson_planner.models import Schedule, ScheduleEntry
from .chromosome import LessonGene, ScheduleChromosome
from .schemas import SchedulingContext, build_scheduling_context


class SchedulePersister:
    @staticmethod
    def persist(
        session: Session,
        chromosome: ScheduleChromosome,
        schedule_name: str,
        is_active: bool = False,
    ) -> Schedule:
        schedule = Schedule(name=schedule_name, is_active=is_active)
        session.add(schedule)
        session.flush()

        for lesson in chromosome.lessons:
            entry = ScheduleEntry(
                schedule_id=schedule.id,
                class_id=lesson.class_id,
                subject_id=lesson.subject_id,
                teacher_id=lesson.teacher_id,
                room_id=lesson.room_id,
                day_of_week=lesson.day,
                slot_id=lesson.slot_id,
            )
            session.add(entry)

        session.commit()
        return schedule

    @staticmethod
    def load_from_db(
        session: Session, schedule_id: UUID
    ) -> tuple[ScheduleChromosome, SchedulingContext]:
        schedule = session.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            raise ValueError(f"Schedule {schedule_id} not found")

        chromosome = ScheduleChromosome(
            lessons=[
                LessonGene(
                    class_id=entry.class_id,
                    subject_id=entry.subject_id,
                    teacher_id=entry.teacher_id,
                    room_id=entry.room_id,
                    day=entry.day_of_week,
                    slot_id=entry.slot_id,
                )
                for entry in schedule.entries
                if entry.class_id and entry.subject_id and entry.teacher_id
                and entry.room_id and entry.day_of_week and entry.slot_id
            ]
        )

        context = build_scheduling_context(session)
        return chromosome, context
