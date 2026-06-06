from __future__ import annotations

from pydantic import BaseModel, field_validator
from typing import Any
import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from lesson_planner.models import GradeLevel, _deterministic_uuid
from lesson_planner.data_imports.base import ImportStatus

logger = logging.getLogger(__name__)


class GradeLevelRow(BaseModel):
    """Pydantic model for grade level CSV rows."""

    name: str
    ordering: int

    @field_validator("ordering", mode="before")
    @classmethod
    def _coerce_ordering(cls, v: Any) -> int:
        try:
            return int(v)
        except Exception as exc:
            raise ValueError("ordering must be an integer") from exc


def upsert(session: Session, row: GradeLevelRow) -> ImportStatus:
    """Insert or update a grade level using a deterministic UUID."""
    grade_id = _deterministic_uuid(str(row.name))
    stmt = insert(GradeLevel).values(
        id=grade_id,
        name=row.name,
        ordering=row.ordering,
    ).on_conflict_do_update(
        index_elements=[GradeLevel.name],
        set_=dict(ordering=row.ordering),
    )
    session.execute(stmt)
    return ImportStatus.imported
