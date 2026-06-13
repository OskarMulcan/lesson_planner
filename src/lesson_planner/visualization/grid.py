from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from uuid import UUID

from lesson_planner.models import DayOfWeek, VisualizationDimension


@dataclass(frozen=True, slots=True)
class SlotInfo:
    """A lesson slot's identity and time window; one grid row."""

    id: UUID
    slot_number: int
    start_time: time
    end_time: time

    @property
    def label(self) -> str:
        return f"{self.start_time.strftime('%H:%M')}\u2013{self.end_time.strftime('%H:%M')}"


@dataclass(frozen=True, slots=True)
class GridCell:
    """A single occupied cell in a schedule grid.

    `title` is the primary label (the thing this entity "is doing" in that
    slot), `subtitle`/`extra` add the remaining two dimensions of context.
    """

    title: str
    subtitle: str = ""
    extra: str = ""

    @property
    def lines(self) -> list[str]:
        return [part for part in (self.title, self.subtitle, self.extra) if part]


@dataclass(slots=True)
class ScheduleGrid:
    """A day/slot template for a single entity (one room, class, or teacher).

    `days` and `slots` define the fixed template (every weekday x every
    lesson slot); `cells` holds only the occupied positions, keyed by
    (day, slot_id).
    """

    dimension: VisualizationDimension
    dimension_id: UUID
    label: str
    days: list[DayOfWeek]
    slots: list[SlotInfo]
    cells: dict[tuple[DayOfWeek, UUID], GridCell] = field(default_factory=dict)

    def cell(self, day: DayOfWeek, slot_id: UUID) -> GridCell | None:
        return self.cells.get((day, slot_id))