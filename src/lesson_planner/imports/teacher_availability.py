from __future__ import annotations

from pydantic import BaseModel, field_validator
from typing import Any
from datetime import date
import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy import select

from lesson_planner.models import Teacher, LessonSlot, TeacherAvailability, DayOfWeek
from lesson_planner.imports.base import ImportStatus

logger = logging.getLogger(__name__)


class TeacherAvailabilityRow(BaseModel):
    """Pydantic model for teacher availability CSV rows."""

    teacher_first_name: str
    teacher_last_name: str
    teacher_employment_date: date
    day_of_week: DayOfWeek
    slot_number: int

    @field_validator("teacher_employment_date", mode="before")
    @classmethod
    def _parse_date(cls, v: Any) -> date:
        if isinstance(v, date):
            return v
        try:
            return date.fromisoformat(v)
        except Exception as exc:
            raise ValueError("teacher_employment_date must be YYYY-MM-DD") from exc

    @field_validator("day_of_week", mode="before")
    @classmethod
    def _coerce_day(cls, v: Any) -> DayOfWeek:
        if isinstance(v, DayOfWeek):
            return v
        try:
            return DayOfWeek[str(v).strip().upper()]
        except Exception as exc:
            raise ValueError("day_of_week must be a valid DayOfWeek") from exc


def _resolve_teacher_id(session: Session, first_name: str, last_name: str, employment_date: date):
    stmt = select(Teacher.id).where(
        Teacher.first_name == first_name,
        Teacher.last_name == last_name,
        Teacher.employment_date == employment_date,
    )
    return session.execute(stmt).scalar_one_or_none()


def _resolve_slot_id(session: Session, slot_number: int):
    stmt = select(LessonSlot.id).where(LessonSlot.slot_number == slot_number)
    return session.execute(stmt).scalar_one_or_none()


def upsert(session: Session, row: TeacherAvailabilityRow) -> ImportStatus:
    """Insert a teacher availability record; skip if it already exists."""
    teacher_id = _resolve_teacher_id(session, row.teacher_first_name, row.teacher_last_name, row.teacher_employment_date)
    if teacher_id is None:
        raise ValueError("Referenced teacher not found")
    slot_id = _resolve_slot_id(session, row.slot_number)
    if slot_id is None:
        raise ValueError("Referenced slot not found")

    exists = session.execute(
        select(TeacherAvailability).where(
            TeacherAvailability.teacher_id == teacher_id,
            TeacherAvailability.day_of_week == row.day_of_week,
            TeacherAvailability.slot_id == slot_id,
        )
    ).scalar_one_or_none()
    if exists:
        return ImportStatus.skipped

    stmt = insert(TeacherAvailability).values(
        teacher_id=teacher_id,
        day_of_week=row.day_of_week,
        slot_id=slot_id,
    )
    session.execute(stmt)
    return ImportStatus.imported
