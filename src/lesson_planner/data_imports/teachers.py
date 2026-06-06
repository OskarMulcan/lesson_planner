from __future__ import annotations

from pydantic import BaseModel, field_validator
from datetime import date
from typing import Any
import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from lesson_planner.models import Teacher, _deterministic_uuid
from lesson_planner.data_imports.base import ImportStatus

logger = logging.getLogger(__name__)


class TeacherRow(BaseModel):
    """Pydantic model for teacher CSV rows."""

    first_name: str
    last_name: str
    employment_date: date
    weekly_hours: int

    @field_validator("employment_date", mode="before")
    @classmethod
    def _parse_date(cls, v: Any) -> date:
        if isinstance(v, date):
            return v
        try:
            return date.fromisoformat(v)
        except Exception as exc:
            raise ValueError("employment_date must be YYYY-MM-DD") from exc


def upsert(session: Session, row: TeacherRow) -> ImportStatus:
    """Insert or update a teacher using a deterministic UUID based on identity.

    Returns ImportStatus.imported on success.
    """
    emp_s = row.employment_date.isoformat()
    key = f"{row.first_name}|{row.last_name}|{emp_s}"
    teacher_id = _deterministic_uuid(key)
    stmt = insert(Teacher).values(
        id=teacher_id,
        first_name=row.first_name,
        last_name=row.last_name,
        employment_date=row.employment_date,
        weekly_hours=row.weekly_hours,
    ).on_conflict_do_update(
        constraint="uq_teacher_identity",
        set_=dict(weekly_hours=row.weekly_hours),
    )
    session.execute(stmt)
    return ImportStatus.imported
