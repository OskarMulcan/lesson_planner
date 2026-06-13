import uuid
from typing import Any, Optional

from sqlalchemy import String, SmallInteger, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, _deterministic_uuid


class RoomType(Base):
    """Room types defining available lesson locations."""

    __tablename__ = "room_types"
    __table_args__ = {"schema": "facilities"}

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if "id" not in kwargs and "name" in kwargs:
            kwargs["id"] = _deterministic_uuid(str(kwargs["name"]))
        super().__init__(*args, **kwargs)


class Room(Base):
    """A physical room where lessons take place."""

    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_room_capacity_positive"),
        {"schema": "facilities"}
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    number: Mapped[str] = mapped_column(String, unique=True)
    floor: Mapped[int] = mapped_column(SmallInteger)
    room_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.room_types.id"))
    capacity: Mapped[Optional[int]] = mapped_column(SmallInteger)

    room_type: Mapped["RoomType"] = relationship(lazy="joined")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if "id" not in kwargs and "number" in kwargs:
            kwargs["id"] = _deterministic_uuid(str(kwargs["number"]))
        super().__init__(*args, **kwargs)