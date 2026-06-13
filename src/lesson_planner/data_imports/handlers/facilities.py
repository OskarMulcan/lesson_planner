from __future__ import annotations
import logging
from typing import Optional, Any
from pydantic import BaseModel, field_validator
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ...models.facilities import Room, RoomType
from ...models.base import _deterministic_uuid
from ..base import ImportStatus

logger = logging.getLogger(__name__)

class RoomRow(BaseModel):
    """Pydantic model for room CSV rows."""
    number: str
    floor: int
    room_type: str
    capacity: Optional[int] = None

    @field_validator("capacity", mode="before")
    @classmethod
    def _coerce_capacity(cls, v: Any) -> Optional[int]:
        if v in (None, "", "null", "NULL"):
            return None
        try:
            val = int(v)
            if val <= 0:
                raise ValueError("Capacity must be positive")
            return val
        except (ValueError, TypeError) as exc:
            raise ValueError("capacity must be a positive integer or empty") from exc

def upsert(session: Session, row: RoomRow) -> ImportStatus:
    existing = session.query(RoomType).filter(RoomType.name.ilike(row.room_type)).one_or_none()
    if existing:
        room_type_id = existing.id
    else:
        rt = RoomType(name=row.room_type)
        session.add(rt)
        session.flush()
        room_type_id = rt.id

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