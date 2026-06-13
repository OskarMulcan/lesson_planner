from __future__ import annotations
import logging
from datetime import time
from typing import Any
from pydantic import BaseModel, field_validator
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ...models.scheduling import LessonSlot
from ...models.base import _deterministic_uuid
from ..base import ImportStatus

logger = logging.getLogger(__name__)


class LessonSlotRow(BaseModel):
    slot_number: int
    start_time: time
    end_time: time

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def _parse_time(cls, v: Any) -> time:
        if isinstance(v, time): return v
        try: return time.fromisoformat(str(v))
        except Exception as exc: raise ValueError("Time must be HH:MM") from exc


def upsert_lesson_slot(session: Session, row: LessonSlotRow) -> ImportStatus:
    slot_id = _deterministic_uuid(str(row.slot_number))
    stmt = insert(LessonSlot).values(
        id=slot_id,
        slot_number=row.slot_number,
        start_time=row.start_time,
        end_time=row.end_time,
    ).on_conflict_do_update(
        index_elements=[LessonSlot.slot_number],
        set_=dict(start_time=row.start_time, end_time=row.end_time),
    )
    session.execute(stmt)
    return ImportStatus.imported