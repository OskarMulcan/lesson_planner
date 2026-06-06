from __future__ import annotations

from pydantic import BaseModel
import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy import select

from lesson_planner.models import Class, GradeLevel, _deterministic_uuid
from lesson_planner.data_imports.base import ImportStatus

logger = logging.getLogger(__name__)


class ClassRow(BaseModel):
    """Pydantic model for class CSV rows."""

    name: str
    grade_level_name: str


def _resolve_or_create_grade_level(session: Session, name: str):
    stmt = select(GradeLevel).where(GradeLevel.name == name)
    existing = session.execute(stmt).scalar_one_or_none()
    if existing:
        return existing.id

    logger.warning("Grade level %s not found; creating with ordering=0", name)
    grade_id = _deterministic_uuid(str(name))
    stmt = insert(GradeLevel).values(id=grade_id, name=name, ordering=0).returning(GradeLevel.id)
    res = session.execute(stmt).scalar_one()
    return res


def upsert(session: Session, row: ClassRow) -> ImportStatus:
    """Insert or update a Class, creating the grade level if needed.

    Returns ImportStatus.imported on success.
    """
    grade_level_id = _resolve_or_create_grade_level(session, row.grade_level_name)
    stmt = insert(Class).values(
        name=row.name,
        grade_level_id=grade_level_id,
    ).on_conflict_do_update(
        index_elements=[Class.name],
        set_=dict(grade_level_id=grade_level_id),
    )
    session.execute(stmt)
    return ImportStatus.imported
