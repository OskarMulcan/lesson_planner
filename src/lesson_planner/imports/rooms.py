from __future__ import annotations

from pydantic import BaseModel, field_validator
from typing import Any
import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from lesson_planner.models import Room, RoomType, _deterministic_uuid
from lesson_planner.imports.base import ImportStatus

logger = logging.getLogger(__name__)


class RoomRow(BaseModel):
    """Pydantic model for room CSV rows."""

    number: str
    floor: int
    room_type: str
    capacity: int | None = None

    @field_validator("capacity", mode="before")
    @classmethod
    def _coerce_capacity(cls, v: Any) -> int | None:
        if v is None or v == "":
            return None
        try:
            return int(v)
        except Exception as exc:
            raise ValueError("capacity must be an integer or empty") from exc


def _resolve_room_type_id(session: Session, name: str):
    existing = session.query(RoomType).filter(RoomType.name.ilike(name)).one_or_none()
    if existing:
        return existing.id
    rt = RoomType(name=name)
    session.add(rt)
    session.flush()
    return rt.id


def upsert(session: Session, row: RoomRow) -> ImportStatus:
    """Insert or update a room, creating room type if needed."""
    room_type_id = _resolve_room_type_id(session, row.room_type)
    room_id = _deterministic_uuid(str(row.number))
    stmt = insert(Room).values(
        id=room_id,
        number=row.number,
        floor=row.floor,
        room_type_id=room_type_id,
        capacity=row.capacity,
    ).on_conflict_do_update(
        index_elements=[Room.number],
        set_=dict(floor=row.floor, room_type_id=room_type_id, capacity=row.capacity),
    )
    session.execute(stmt)
    return ImportStatus.imported
