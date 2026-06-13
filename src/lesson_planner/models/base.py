import enum
import uuid
from sqlalchemy.orm import DeclarativeBase

LESSON_PLANNER_NS = uuid.UUID("7f9c5a3c-e4f2-4c95-8e25-2a1f4b7d3c9a")


def _deterministic_uuid(*parts: str) -> uuid.UUID:
    return uuid.uuid5(LESSON_PLANNER_NS, "|".join(parts))


class Base(DeclarativeBase):
    pass


class DayOfWeek(enum.Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"