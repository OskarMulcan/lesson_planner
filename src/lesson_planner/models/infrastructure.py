import datetime
import enum
import uuid
from typing import Any, Optional, TYPE_CHECKING

from sqlalchemy import (
    String, Integer, JSON, DateTime, Text, LargeBinary,
    ForeignKey, UniqueConstraint, text, func, event, DDL
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum

from .base import Base

if TYPE_CHECKING:
    from .scheduling import Schedule


class ImportStaging(Base):
    """A staging table for data imports."""

    __tablename__ = "import_staging"
    __table_args__ = {"prefetch_rows": 0, "schema": "integration"}

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    session_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True))
    target_table: Mapped[str] = mapped_column(String)
    row_number: Mapped[int] = mapped_column(Integer)
    raw_data: Mapped[Any] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default="pending")
    error_detail: Mapped[Optional[str]] = mapped_column(String)
    processed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True))


event.listen(
    ImportStaging.__table__, "after_create", DDL("ALTER TABLE integration.import_staging SET UNLOGGED")
)


class VisualizationDimension(enum.Enum):
    """The schedule dimension a visualization is rendered for."""
    ROOM = "ROOM"
    CLASS = "CLASS"
    TEACHER = "TEACHER"


class ScheduleVisualization(Base):
    """A rendered HTML/PNG schedule grid for one entity of one dimension."""

    __tablename__ = "schedule_visualizations"
    __table_args__ = (
        UniqueConstraint("schedule_id", "dimension", "dimension_id", name="uq_schedule_visualization_target"),
        {"schema": "integration"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    schedule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schedule.schedules.id", ondelete="CASCADE"))

    dimension: Mapped[VisualizationDimension] = mapped_column(
        SAEnum(VisualizationDimension, name="visualization_dimension", schema="integration", native_enum=True)
    )
    dimension_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True))

    label: Mapped[str] = mapped_column(String)
    html_content: Mapped[Optional[str]] = mapped_column(Text)
    png_content: Mapped[Optional[bytes]] = mapped_column(LargeBinary)

    generated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), onupdate=func.now()
    )

    schedule: Mapped["Schedule"] = relationship(lazy="joined")