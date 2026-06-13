import datetime
import uuid
from typing import Any, Optional, TYPE_CHECKING

from sqlalchemy import (
    SmallInteger, Time, Boolean, DateTime, ForeignKey,
    CheckConstraint, Index, text, event, DDL, String
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum

from .base import Base, _deterministic_uuid, DayOfWeek

if TYPE_CHECKING:
    from .academic import Class, Subject
    from .staff import Teacher
    from .facilities import Room


class LessonSlot(Base):
    """A lesson slot describing a numbered time window."""

    __tablename__ = "lesson_slots"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_lesson_slot_time_order"),
        {"schema": "schedule"},
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    slot_number: Mapped[int] = mapped_column(SmallInteger, unique=True)
    start_time: Mapped[datetime.time] = mapped_column(Time)
    end_time: Mapped[datetime.time] = mapped_column(Time)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if "id" not in kwargs and "slot_number" in kwargs:
            kwargs["id"] = _deterministic_uuid(str(kwargs["slot_number"]))
        super().__init__(*args, **kwargs)


event.listen(
    LessonSlot.__table__,
    "after_create",
    DDL(
        "ALTER TABLE schedule.lesson_slots ADD CONSTRAINT lesson_slots_no_overlap "
        "EXCLUDE USING GIST ((tsrange((date '2000-01-01' + start_time), (date '2000-01-01' + end_time))) WITH &&)"
    ),
)


class Schedule(Base):
    """A schedule container for schedule entries."""

    __tablename__ = "schedules"
    __table_args__ = {"schema": "schedule"}

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String, unique=True)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))

    entries: Mapped[list["ScheduleEntry"]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan"
    )


class ScheduleEntry(Base):
    """A single assignment within a schedule."""

    __tablename__ = "schedule_entries"
    __table_args__ = (
        Index(
            "uq_schedule_class_day_slot", "schedule_id", "class_id", "day_of_week", "slot_id", unique=True,
            postgresql_where=text("class_id IS NOT NULL AND day_of_week IS NOT NULL AND slot_id IS NOT NULL"),
        ),
        Index(
            "uq_schedule_teacher_day_slot", "schedule_id", "teacher_id", "day_of_week", "slot_id", unique=True,
            postgresql_where=text("teacher_id IS NOT NULL AND day_of_week IS NOT NULL AND slot_id IS NOT NULL"),
        ),
        Index(
            "uq_schedule_room_day_slot", "schedule_id", "room_id", "day_of_week", "slot_id", unique=True,
            postgresql_where=text("room_id IS NOT NULL AND day_of_week IS NOT NULL AND slot_id IS NOT NULL"),
        ),
        {"schema": "schedule"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    schedule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schedule.schedules.id"))
    class_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("academic.classes.id"))
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("academic.subjects.id"))
    teacher_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("staff.teachers.id"))
    room_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("facilities.rooms.id"))
    day_of_week: Mapped[Optional[DayOfWeek]] = mapped_column(
        SAEnum(DayOfWeek, name="day_of_week", schema="schedule", native_enum=True)
    )
    slot_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("schedule.lesson_slots.id"))

    schedule: Mapped["Schedule"] = relationship(back_populates="entries", lazy="joined")
    klass: Mapped[Optional["Class"]] = relationship(lazy="joined")
    subject: Mapped[Optional["Subject"]] = relationship(lazy="joined")
    teacher: Mapped[Optional["Teacher"]] = relationship(lazy="joined")
    room: Mapped[Optional["Room"]] = relationship(lazy="joined")
    slot: Mapped[Optional["LessonSlot"]] = relationship(lazy="joined")
    