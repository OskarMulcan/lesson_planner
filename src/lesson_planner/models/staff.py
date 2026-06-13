import datetime
import uuid
from typing import Any, TYPE_CHECKING

from sqlalchemy import String, SmallInteger, Date, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum

from .base import Base, _deterministic_uuid, DayOfWeek

if TYPE_CHECKING:
    from .academic import Subject
    from .scheduling import LessonSlot


class Teacher(Base):
    """A teacher with employment information."""

    __tablename__ = "teachers"
    __table_args__ = (
        UniqueConstraint("first_name", "last_name", "employment_date", name="uq_teacher_identity"),
        {"schema": "staff"},
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    employment_date: Mapped[datetime.date] = mapped_column(Date)
    weekly_hours: Mapped[int] = mapped_column(SmallInteger)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if "id" not in kwargs:
            if all(k in kwargs for k in ("first_name", "last_name", "employment_date")):
                emp = kwargs["employment_date"]
                emp_s = emp.isoformat() if isinstance(emp, datetime.date) else str(emp)
                kwargs["id"] = _deterministic_uuid(
                    kwargs['first_name'], kwargs['last_name'], emp_s
                )
        super().__init__(*args, **kwargs)


class TeacherSubject(Base):
    """Bridge table linking teachers and subjects."""

    __tablename__ = "teacher_subjects"
    __table_args__ = {"schema": "staff"}

    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff.teachers.id"), primary_key=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic.subjects.id"), primary_key=True)

    teacher: Mapped["Teacher"] = relationship(lazy="joined")
    subject: Mapped["Subject"] = relationship(lazy="joined")


class TeacherAvailability(Base):
    """Bridge table recording a teacher's available slots per weekday."""

    __tablename__ = "teacher_availability"
    __table_args__ = {"schema": "staff"}

    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff.teachers.id"), primary_key=True)
    day_of_week: Mapped[DayOfWeek] = mapped_column(
        SAEnum(DayOfWeek, name="day_of_week", schema="staff", native_enum=True), primary_key=True
    )
    slot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schedule.lesson_slots.id"), primary_key=True)

    teacher: Mapped["Teacher"] = relationship(lazy="joined")
    slot: Mapped["LessonSlot"] = relationship(lazy="joined")