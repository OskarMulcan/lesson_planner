import uuid
from typing import Any, TYPE_CHECKING

from sqlalchemy import String, SmallInteger, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, _deterministic_uuid

if TYPE_CHECKING:
    from .facilities import RoomType


class Subject(Base):
    """A school subject."""

    __tablename__ = "subjects"
    __table_args__ = {"schema": "academic"}

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    required_room_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.room_types.id"))

    required_room_type: Mapped["RoomType"] = relationship(lazy="joined")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if "id" not in kwargs and "code" in kwargs:
            kwargs["id"] = _deterministic_uuid(str(kwargs["code"]))
        super().__init__(*args, **kwargs)


class GradeLevel(Base):
    """A grade level such as Year 7 or Grade 10."""

    __tablename__ = "grade_levels"
    __table_args__ = {"schema": "academic"}

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    ordering: Mapped[int] = mapped_column(SmallInteger)

    classes: Mapped[list["Class"]] = relationship(back_populates="grade_level")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if "id" not in kwargs and "name" in kwargs:
            kwargs["id"] = _deterministic_uuid(str(kwargs["name"]))
        super().__init__(*args, **kwargs)


class Class(Base):
    """A student class grouping."""

    __tablename__ = "classes"
    __table_args__ = {"schema": "academic"}

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String, unique=True)
    grade_level_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic.grade_levels.id"))

    grade_level: Mapped["GradeLevel"] = relationship(back_populates="classes", lazy="selectin")


class GradeSubjectRequirement(Base):
    """Bridge table linking grade levels and subjects with weekly lesson counts."""

    __tablename__ = "grade_subject_requirements"
    __table_args__ = {"schema": "academic"}

    grade_level_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic.grade_levels.id"), primary_key=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic.subjects.id"), primary_key=True)
    lessons_per_week: Mapped[int] = mapped_column(SmallInteger)

    grade_level: Mapped["GradeLevel"] = relationship(lazy="joined")
    subject: Mapped["Subject"] = relationship(lazy="joined")