from __future__ import annotations
import logging
from datetime import date
from pydantic import BaseModel, field_validator
from typing import Any
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy import select

from ...models.academic import Subject
from ...models.staff import Teacher, TeacherSubject, TeacherAvailability, DayOfWeek
from ...models.scheduling import LessonSlot
from ...models.base import _deterministic_uuid
from ..base import ImportStatus

logger = logging.getLogger(__name__)


class TeacherRow(BaseModel):
    first_name: str
    last_name: str
    employment_date: date
    weekly_hours: int

    @field_validator("employment_date", mode="before")
    @classmethod
    def _parse_date(cls, v: Any) -> date:
        return v if isinstance(v, date) else date.fromisoformat(str(v))

class TeacherSubjectRow(BaseModel):
    teacher_first_name: str
    teacher_last_name: str
    teacher_employment_date: date
    subject_code: str

class TeacherAvailabilityRow(BaseModel):
    teacher_first_name: str
    teacher_last_name: str
    teacher_employment_date: date
    day_of_week: DayOfWeek
    slot_number: int


def upsert_teacher(session: Session, row: TeacherRow) -> ImportStatus:
    key = f"{row.first_name}|{row.last_name}|{row.employment_date.isoformat()}"
    t_id = _deterministic_uuid(key)
    stmt = insert(Teacher).values(
        id=t_id,
        first_name=row.first_name,
        last_name=row.last_name, 
        employment_date=row.employment_date,
        weekly_hours=row.weekly_hours
    ).on_conflict_do_update(
        index_elements=[Teacher.first_name, Teacher.last_name, Teacher.employment_date], 
        set_=dict(weekly_hours=row.weekly_hours)
    )
    session.execute(stmt)
    return ImportStatus.imported

def upsert_teacher_subject(session: Session, row: TeacherSubjectRow) -> ImportStatus:
    t_id = session.scalar(select(Teacher.id).where(
        Teacher.first_name == row.teacher_first_name, 
        Teacher.last_name == row.teacher_last_name, 
        Teacher.employment_date == row.teacher_employment_date
    ))
    s_id = session.scalar(select(Subject.id).where(Subject.code == row.subject_code))
    
    if not t_id or not s_id:
        raise ValueError("Teacher or Subject not found")
    
    stmt = insert(TeacherSubject).values(teacher_id=t_id, subject_id=s_id).on_conflict_do_nothing()
    session.execute(stmt)
    return ImportStatus.imported

def upsert_teacher_availability(session: Session, row: TeacherAvailabilityRow) -> ImportStatus:
    t_id = session.scalar(select(Teacher.id).where(Teacher.first_name == row.teacher_first_name, 
                                                   Teacher.last_name == row.teacher_last_name, 
                                                   Teacher.employment_date == row.teacher_employment_date))
    s_id = session.scalar(select(LessonSlot.id).where(LessonSlot.slot_number == row.slot_number))
    
    if not t_id or not s_id: raise ValueError("Teacher or Slot not found")
    
    stmt = insert(TeacherAvailability).values(
        teacher_id=t_id, day_of_week=row.day_of_week, slot_id=s_id
    ).on_conflict_do_nothing()
    session.execute(stmt)
    return ImportStatus.imported