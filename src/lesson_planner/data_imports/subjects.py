from __future__ import annotations

from pydantic import BaseModel, field_validator
from typing import Any
import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from lesson_planner.models import Subject, RoomType, _deterministic_uuid
from lesson_planner.data_imports.base import ImportStatus

logger = logging.getLogger(__name__)


class SubjectRow(BaseModel):
    """Pydantic model for subject CSV rows."""

    code: str
    name: str
    required_room_type: str

    @field_validator("required_room_type", mode="before")
    @classmethod
    def _coerce_room_type(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.strip()
        return str(v)


def _resolve_room_type_id(session: Session, name: str):
    existing = session.query(RoomType).filter(RoomType.name.ilike(name)).one_or_none()
    if existing:
        return existing.id
    rt = RoomType(name=name)
    session.add(rt)
    session.flush()
    return rt.id


def upsert(session: Session, row: SubjectRow) -> ImportStatus:
    """Insert or update a subject. Creates required room type if missing."""
    room_type_id = _resolve_room_type_id(session, row.required_room_type)
    subject_id = _deterministic_uuid(str(row.code))
    stmt = insert(Subject).values(
        id=subject_id,
        code=row.code,
        name=row.name,
        required_room_type_id=room_type_id,
    ).on_conflict_do_update(
        index_elements=[Subject.code],
        set_=dict(name=row.name, required_room_type_id=room_type_id),
    )
    session.execute(stmt)
    return ImportStatus.imported
