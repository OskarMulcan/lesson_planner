from __future__ import annotations

from pydantic import BaseModel, field_validator
from datetime import date
from typing import Any
import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy import select

from lesson_planner.models import Teacher, Subject, TeacherSubject
from lesson_planner.data_imports.base import ImportStatus

logger = logging.getLogger(__name__)


class TeacherSubjectRow(BaseModel):
    """Pydantic model for teacher-subject CSV rows."""

    teacher_first_name: str
    teacher_last_name: str
    teacher_employment_date: date
    subject_code: str

    @field_validator("teacher_employment_date", mode="before")
    @classmethod
    def _parse_date(cls, v: Any) -> date:
        if isinstance(v, date):
            return v
        try:
            return date.fromisoformat(v)
        except Exception as exc:
            raise ValueError("teacher_employment_date must be YYYY-MM-DD") from exc


def _resolve_teacher_id(session: Session, first_name: str, last_name: str, employment_date: date):
    stmt = select(Teacher.id).where(
        Teacher.first_name == first_name,
        Teacher.last_name == last_name,
        Teacher.employment_date == employment_date,
    )
    res = session.execute(stmt).scalar_one_or_none()
    return res


def _resolve_subject_id(session: Session, code: str):
    stmt = select(Subject.id).where(Subject.code == code)
    return session.execute(stmt).scalar_one_or_none()


def upsert(session: Session, row: TeacherSubjectRow) -> ImportStatus:
    """Insert a teacher-subject link. Returns 'skipped' if the link already exists."""
    teacher_id = _resolve_teacher_id(session, row.teacher_first_name, row.teacher_last_name, row.teacher_employment_date)
    if teacher_id is None:
        raise ValueError("Referenced teacher not found")
    subject_id = _resolve_subject_id(session, row.subject_code)
    if subject_id is None:
        raise ValueError("Referenced subject not found")

    exists = session.execute(
        select(TeacherSubject).where(
            TeacherSubject.teacher_id == teacher_id,
            TeacherSubject.subject_id == subject_id,
        )
    ).scalar_one_or_none()
    if exists:
        return ImportStatus.skipped

    stmt = insert(TeacherSubject).values(
        teacher_id=teacher_id,
        subject_id=subject_id,
    )
    session.execute(stmt)
    return ImportStatus.imported
