import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from lesson_planner.models import Schedule, ScheduleEntry
from .chromosome import LessonGene, ScheduleChromosome
from .repairs import RepairsOperator
from .schemas import SchedulingContext, build_scheduling_context

logger = logging.getLogger(__name__)


class SchedulePersister:
    @staticmethod
    def persist(
        session: Session,
        chromosome: Optional[ScheduleChromosome],
        schedule_name: str,
        is_active: bool = False,
    ) -> Optional[Schedule]:
        """Persist ``chromosome`` as a new ``Schedule`` with its
        ``ScheduleEntry`` rows.

        Returns ``None`` (without touching the database) instead of raising
        when ``chromosome`` is ``None`` - ``GeneticEngine.run`` reported the
        schedule as unachievable, so there is nothing to save.

        A genuine ``IntegrityError`` while inserting is still treated as an
        unexpected error and re-raised as a ``RuntimeError``, since by this
        point the chromosome has already passed the checks above.
        """
        if chromosome is None:
            logger.error(
                "Refusing to persist schedule '%s': no chromosome was supplied "
                "(no achievable schedule was found).",
                schedule_name,
            )
            return None

        try:
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

        except IntegrityError as exc:
            session.rollback()

            logger.error(
                "Database integrity violation while persisting schedule '%s'. Details: %s",
                schedule_name, exc.orig
            )
            raise RuntimeError(f"Database constraint validation failed: {exc.orig}") from exc

        except Exception:
            session.rollback()
            logger.exception("Unexpected system error occurred while persisting schedule '%s'", schedule_name)
            raise

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