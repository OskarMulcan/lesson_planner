from __future__ import annotations
import logging
import re
from datetime import date, datetime, time
from pydantic import BaseModel, field_validator
from typing import Any, List, Tuple, Set

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, and_, tuple_

from ...models.academic import Subject
from ...models.staff import Teacher, TeacherSubject, TeacherAvailability, DayOfWeek
from ...models.scheduling import LessonSlot
from ...models.base import _deterministic_uuid
from ..base import ImportStatus

logger = logging.getLogger(__name__)


class TeacherImportRow(BaseModel):
    first_name: str
    last_name: str
    employment_date: date
    weekly_hours: int
    subjects: str = ""
    availability: str = ""

    @field_validator("employment_date", mode="before")
    @classmethod
    def _parse_date(cls, v: Any) -> date:
        return v if isinstance(v, date) else date.fromisoformat(str(v))


def _parse_availability(avail_str: str) -> List[Tuple[DayOfWeek, time, time]]:
    """Parses availability ranges from strings like `DAY:HH:MM-HH:MM` separated by `;`."""
    parsed = []
    if not avail_str:
        return parsed

    for part in avail_str.split(';'):
        part = part.strip()
        if not part:
            continue
            
        match = re.match(r'^([A-Z]+)\s*:\s*(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})$', part.upper())
        if match:
            day_str, start_str, end_str = match.groups()
            try:
                day_enum = DayOfWeek[day_str]
                st = datetime.strptime(start_str, "%H:%M").time()
                et = datetime.strptime(end_str, "%H:%M").time()
                parsed.append((day_enum, st, et))
            except (KeyError, ValueError):
                logger.warning(f"Failed to parse availability segment: {part}")
    return parsed


def upsert_teacher_full(session: Session, row: TeacherImportRow) -> ImportStatus:
    emp_s = row.employment_date.isoformat()
    t_id = _deterministic_uuid(row.first_name, row.last_name, emp_s)
    
    stmt = insert(Teacher).values(
        id=t_id,
        first_name=row.first_name,
        last_name=row.last_name, 
        employment_date=row.employment_date,
        weekly_hours=row.weekly_hours
    ).on_conflict_do_update(
        index_elements=["first_name", "last_name", "employment_date"], 
        set_=dict(weekly_hours=row.weekly_hours)
    )
    session.execute(stmt)

    new_subject_codes = [c.strip() for c in row.subjects.split(";") if c.strip()]
    new_subject_ids = set()
    if new_subject_codes:
        new_subject_ids = set(
            session.scalars(select(Subject.id).where(Subject.code.in_(new_subject_codes))).all()
        )

    existing_subject_ids = set(
        session.scalars(select(TeacherSubject.subject_id).where(TeacherSubject.teacher_id == t_id)).all()
    )

    subjects_to_add = new_subject_ids - existing_subject_ids
    subjects_to_remove = existing_subject_ids - new_subject_ids

    if subjects_to_remove:
        session.execute(
            delete(TeacherSubject).where(
                and_(
                    TeacherSubject.teacher_id == t_id,
                    TeacherSubject.subject_id.in_(subjects_to_remove)
                )
            )
        )

    if subjects_to_add:
        session.execute(
            insert(TeacherSubject).values([
                {"teacher_id": t_id, "subject_id": s_id} for s_id in subjects_to_add
            ]).on_conflict_do_nothing()
        )

    avail_ranges = _parse_availability(row.availability)
    
    all_slots = session.execute(
        select(LessonSlot.id, LessonSlot.start_time, LessonSlot.end_time)
    ).all()

    new_avail_pairs: Set[Tuple[DayOfWeek, Any]] = set()
    for day, st, et in avail_ranges:
        for slot in all_slots:
            if slot.start_time >= st and slot.end_time <= et:
                new_avail_pairs.add((day, slot.id))

    existing_avail = session.execute(
        select(TeacherAvailability.day_of_week, TeacherAvailability.slot_id)
        .where(TeacherAvailability.teacher_id == t_id)
    ).all()
    existing_avail_pairs = set((row.day_of_week, row.slot_id) for row in existing_avail)

    avail_to_add = new_avail_pairs - existing_avail_pairs
    avail_to_remove = existing_avail_pairs - new_avail_pairs

    if avail_to_remove:
        session.execute(
            delete(TeacherAvailability).where(
                and_(
                    TeacherAvailability.teacher_id == t_id,
                    tuple_(TeacherAvailability.day_of_week, TeacherAvailability.slot_id).in_(avail_to_remove)
                )
            )
        )

    if avail_to_add:
        session.execute(
            insert(TeacherAvailability).values([
                {"teacher_id": t_id, "day_of_week": day, "slot_id": s_id}
                for day, s_id in avail_to_add
            ]).on_conflict_do_nothing()
        )

    return ImportStatus.imported