from __future__ import annotations

from pydantic import BaseModel, field_validator
from datetime import time
from typing import Any
import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from lesson_planner.models import LessonSlot, _deterministic_uuid
from lesson_planner.imports.base import ImportStatus

logger = logging.getLogger(__name__)


class LessonSlotRow(BaseModel):
    """Pydantic model for lesson slot CSV rows."""

    slot_number: int
    start_time: time
    end_time: time

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def _parse_time(cls, v: Any) -> time:
        if isinstance(v, time):
            return v
        try:
            return time.fromisoformat(v)
        except Exception as exc:
            raise ValueError("start_time and end_time must be HH:MM") from exc


def upsert(session: Session, row: LessonSlotRow) -> ImportStatus:
    """Insert or update a lesson slot by slot_number.

    Returns ImportStatus.imported on success.
    """
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
