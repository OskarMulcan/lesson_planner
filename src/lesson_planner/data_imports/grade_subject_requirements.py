from __future__ import annotations

from pydantic import BaseModel, field_validator
from typing import Any
import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy import select

from lesson_planner.models import GradeLevel, Subject, GradeSubjectRequirement
from lesson_planner.data_imports.base import ImportStatus

logger = logging.getLogger(__name__)


class GradeSubjectRequirementRow(BaseModel):
    """Pydantic model for grade-subject requirement CSV rows."""

    grade_level_name: str
    subject_code: str
    lessons_per_week: int

    @field_validator("lessons_per_week", mode="before")
    @classmethod
    def _coerce_lessons(cls, v: Any) -> int:
        try:
            return int(v)
        except Exception as exc:
            raise ValueError("lessons_per_week must be an integer") from exc


def _resolve_grade_level_id(session: Session, name: str):
    stmt = select(GradeLevel.id).where(GradeLevel.name == name)
    return session.execute(stmt).scalar_one_or_none()


def _resolve_subject_id(session: Session, code: str):
    stmt = select(Subject.id).where(Subject.code == code)
    return session.execute(stmt).scalar_one_or_none()


def upsert(session: Session, row: GradeSubjectRequirementRow) -> ImportStatus:
    """Insert or update a grade-subject requirement with lessons per week."""
    grade_level_id = _resolve_grade_level_id(session, row.grade_level_name)
    if grade_level_id is None:
        raise ValueError("Referenced grade_level not found")
    subject_id = _resolve_subject_id(session, row.subject_code)
    if subject_id is None:
        raise ValueError("Referenced subject not found")

    stmt = insert(GradeSubjectRequirement).values(
        grade_level_id=grade_level_id,
        subject_id=subject_id,
        lessons_per_week=row.lessons_per_week,
    ).on_conflict_do_update(
        index_elements=[GradeSubjectRequirement.grade_level_id, GradeSubjectRequirement.subject_id],
        set_=dict(lessons_per_week=row.lessons_per_week),
    )
    session.execute(stmt)
    return ImportStatus.imported
