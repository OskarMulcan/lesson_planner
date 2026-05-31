from __future__ import annotations

import uuid
import enum
from typing import Optional
from datetime import date, datetime, time

from sqlalchemy import (
    Column,
    String,
    Integer,
    SmallInteger,
    Date,
    DateTime,
    Time,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
    Float,
    JSON,
    PrimaryKeyConstraint,
    and_,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.types import Enum as SAEnum
from sqlalchemy import event, DDL

Base = declarative_base()

LESSON_PLANNER_NS = uuid.UUID("7f9c5a3c-e4f2-4c95-8e25-2a1f4b7d3c9a")


def _deterministic_uuid(*parts: str) -> uuid.UUID:
    return uuid.uuid5(LESSON_PLANNER_NS, "|".join(parts))


class DayOfWeek(enum.Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"


class RoomType(enum.Enum):
    STANDARD = "STANDARD"
    LAB = "LAB"
    GYM = "GYM"
    WORKSHOP = "WORKSHOP"
    COMPUTER_LAB = "COMPUTER_LAB"


class LessonSlot(Base):
    """A lesson slot describing a numbered time window.

    Args:
        None

    Returns:
        ORM mapped LessonSlot
    """

    __tablename__ = "lesson_slots"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    slot_number = Column(SmallInteger, unique=True, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_lesson_slot_time_order"),
    )

    def __init__(self, *args, **kwargs):
        if "id" not in kwargs and "slot_number" in kwargs:
            kwargs["id"] = _deterministic_uuid(str(kwargs["slot_number"]))
        super().__init__(*args, **kwargs)


event.listen(Base.metadata, "before_create", DDL("CREATE EXTENSION IF NOT EXISTS btree_gist"))

event.listen(
    LessonSlot.__table__,
    "after_create",
    DDL(
        "ALTER TABLE %(table)s ADD CONSTRAINT lesson_slots_no_overlap "
        "EXCLUDE USING GIST ((tsrange(start_time::timestamp, end_time::timestamp)) WITH &&)"
    ),
)


class Room(Base):
    """A physical room where lessons take place.

    Args:
        None

    Returns:
        ORM mapped Room
    """

    __tablename__ = "rooms"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    number = Column(String, unique=True, nullable=False)
    floor = Column(SmallInteger, nullable=False)
    room_type = Column(SAEnum(RoomType, name="room_type", native_enum=True), nullable=False)
    capacity = Column(SmallInteger, nullable=True)

    def __init__(self, *args, **kwargs):
        if "id" not in kwargs and "number" in kwargs:
            kwargs["id"] = _deterministic_uuid(str(kwargs["number"]))
        super().__init__(*args, **kwargs)


class Teacher(Base):
    """A teacher with employment information.

    Args:
        None

    Returns:
        ORM mapped Teacher
    """

    __tablename__ = "teachers"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    employment_date = Column(Date, nullable=False)
    weekly_hours = Column(SmallInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint("first_name", "last_name", "employment_date", name="uq_teacher_identity"),
    )

    def __init__(self, *args, **kwargs):
        if "id" not in kwargs:
            required = ("first_name", "last_name", "employment_date")
            if all(k in kwargs for k in required):
                emp = kwargs["employment_date"]
                if isinstance(emp, date):
                    emp_s = emp.isoformat()
                else:
                    emp_s = str(emp)
                key = f"{kwargs['first_name']}|{kwargs['last_name']}|{emp_s}"
                kwargs["id"] = _deterministic_uuid(key)
        super().__init__(*args, **kwargs)


class Subject(Base):
    """A school subject.

    Args:
        None

    Returns:
        ORM mapped Subject
    """

    __tablename__ = "subjects"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    required_room_type = Column(
        SAEnum(RoomType, name="room_type", native_enum=True),
        nullable=False,
    )

    def __init__(self, *args, **kwargs):
        if "id" not in kwargs and "code" in kwargs:
            kwargs["id"] = _deterministic_uuid(str(kwargs["code"]))
        super().__init__(*args, **kwargs)


class GradeLevel(Base):
    """A grade level such as Year 7 or Grade 10.

    Args:
        None

    Returns:
        ORM mapped GradeLevel
    """

    __tablename__ = "grade_levels"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    name = Column(String, unique=True, nullable=False)
    ordering = Column(SmallInteger, nullable=False)

    def __init__(self, *args, **kwargs):
        if "id" not in kwargs and "name" in kwargs:
            kwargs["id"] = _deterministic_uuid(str(kwargs["name"]))
        super().__init__(*args, **kwargs)


class Class(Base):
    """A student class grouping.

    Args:
        None

    Returns:
        ORM mapped Class
    """

    __tablename__ = "classes"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name = Column(String, unique=True, nullable=False)
    grade_level_id = Column(PG_UUID(as_uuid=True), ForeignKey("grade_levels.id"), nullable=False)

    grade_level = relationship("GradeLevel", backref="classes", lazy="selectin")


class GradeSubjectRequirement(Base):
    """Bridge table linking grade levels and subjects with weekly lesson counts.

    Args:
        None

    Returns:
        ORM mapped GradeSubjectRequirement
    """

    __tablename__ = "grade_subject_requirements"

    grade_level_id = Column(PG_UUID(as_uuid=True), ForeignKey("grade_levels.id"), primary_key=True)
    subject_id = Column(PG_UUID(as_uuid=True), ForeignKey("subjects.id"), primary_key=True)
    lessons_per_week = Column(SmallInteger, nullable=False)

    grade_level = relationship("GradeLevel", lazy="joined")
    subject = relationship("Subject", lazy="joined")


class TeacherSubject(Base):
    """Bridge table linking teachers and subjects.

    Args:
        None

    Returns:
        ORM mapped TeacherSubject
    """

    __tablename__ = "teacher_subjects"

    teacher_id = Column(PG_UUID(as_uuid=True), ForeignKey("teachers.id"), primary_key=True)
    subject_id = Column(PG_UUID(as_uuid=True), ForeignKey("subjects.id"), primary_key=True)

    teacher = relationship("Teacher", lazy="joined")
    subject = relationship("Subject", lazy="joined")


class TeacherAvailability(Base):
    """Bridge table recording a teacher's available slots per weekday.

    Args:
        None

    Returns:
        ORM mapped TeacherAvailability
    """

    __tablename__ = "teacher_availability"

    teacher_id = Column(PG_UUID(as_uuid=True), ForeignKey("teachers.id"), primary_key=True)
    day_of_week = Column(SAEnum(DayOfWeek, name="day_of_week", native_enum=True), primary_key=True)
    slot_id = Column(PG_UUID(as_uuid=True), ForeignKey("lesson_slots.id"), primary_key=True)

    teacher = relationship("Teacher", lazy="joined")
    slot = relationship("LessonSlot", lazy="joined")


class Schedule(Base):
    """A schedule container for schedule entries.

    Args:
        None

    Returns:
        ORM mapped Schedule
    """

    __tablename__ = "schedules"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    is_active = Column(SmallInteger, nullable=False, default=0)

    @property
    def active(self) -> bool:
        return bool(self.is_active)


class ScheduleEntry(Base):
    """A single assignment within a schedule.

    Args:
        None

    Returns:
        ORM mapped ScheduleEntry
    """

    __tablename__ = "schedule_entries"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    schedule_id = Column(PG_UUID(as_uuid=True), ForeignKey("schedules.id"), nullable=False)
    class_id = Column(PG_UUID(as_uuid=True), ForeignKey("classes.id"), nullable=True)
    subject_id = Column(PG_UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=True)
    teacher_id = Column(PG_UUID(as_uuid=True), ForeignKey("teachers.id"), nullable=True)
    room_id = Column(PG_UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=True)
    day_of_week = Column(SAEnum(DayOfWeek, name="day_of_week", native_enum=True), nullable=True)
    slot_id = Column(PG_UUID(as_uuid=True), ForeignKey("lesson_slots.id"), nullable=True)

    schedule = relationship("Schedule", lazy="joined")
    klass = relationship("Class", lazy="joined")
    subject = relationship("Subject", lazy="joined")
    teacher = relationship("Teacher", lazy="joined")
    room = relationship("Room", lazy="joined")
    slot = relationship("LessonSlot", lazy="joined")

    __table_args__ = (
        Index(
            "uq_schedule_class_day_slot",
            "schedule_id",
            "class_id",
            "day_of_week",
            "slot_id",
            unique=True,
            postgresql_where=and_(
                Column("class_id") != None,
                Column("day_of_week") != None,
                Column("slot_id") != None,
            ),
        ),
        Index(
            "uq_schedule_teacher_day_slot",
            "schedule_id",
            "teacher_id",
            "day_of_week",
            "slot_id",
            unique=True,
            postgresql_where=and_(
                Column("teacher_id") != None,
                Column("day_of_week") != None,
                Column("slot_id") != None,
            ),
        ),
        Index(
            "uq_schedule_room_day_slot",
            "schedule_id",
            "room_id",
            "day_of_week",
            "slot_id",
            unique=True,
            postgresql_where=and_(
                Column("room_id") != None,
                Column("day_of_week") != None,
                Column("slot_id") != None,
            ),
        ),
    )


class ScheduleEntryDraft(Base):
    """A draft schedule entry used during scheduling operations.

    Args:
        None

    Returns:
        ORM mapped ScheduleEntryDraft
    """

    __tablename__ = "schedule_entry_drafts"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    schedule_id = Column(PG_UUID(as_uuid=True), nullable=True)
    class_id = Column(PG_UUID(as_uuid=True), nullable=True)
    class_name = Column(String, nullable=True)
    subject_id = Column(PG_UUID(as_uuid=True), nullable=True)
    subject_name = Column(String, nullable=True)
    subject_code = Column(String, nullable=True)
    required_room_type = Column(SAEnum(RoomType, name="room_type", native_enum=True), nullable=True)
    teacher_id = Column(PG_UUID(as_uuid=True), nullable=True)
    teacher_first_name = Column(String, nullable=True)
    teacher_last_name = Column(String, nullable=True)
    room_id = Column(PG_UUID(as_uuid=True), nullable=True)
    room_number = Column(String, nullable=True)
    room_type = Column(SAEnum(RoomType, name="room_type", native_enum=True), nullable=True)
    day_of_week = Column(SAEnum(DayOfWeek, name="day_of_week", native_enum=True), nullable=True)
    slot_id = Column(PG_UUID(as_uuid=True), ForeignKey("lesson_slots.id"), nullable=True)
    generation = Column(Integer, nullable=True)
    individual_index = Column(Integer, nullable=True)
    fitness_score = Column(Float, nullable=True)
    is_cache = Column(SmallInteger, nullable=False, default=0)

    @property
    def cache(self) -> bool:
        return bool(self.is_cache)


class ImportStaging(Base):
    """A staging table for data imports.

    Args:
        None

    Returns:
        ORM mapped ImportStaging
    """

    __tablename__ = "import_staging"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    session_id = Column(PG_UUID(as_uuid=True), nullable=False)
    target_table = Column(String, nullable=False)
    row_number = Column(Integer, nullable=False)
    raw_data = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default="pending")
    error_detail = Column(String, nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
