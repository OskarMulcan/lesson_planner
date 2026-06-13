from __future__ import annotations
import logging
from typing import Any
from pydantic import BaseModel, field_validator
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy import select

from ...models.academic import Subject, GradeLevel, Class, GradeSubjectRequirement
from ...models.facilities import RoomType
from ...models.base import _deterministic_uuid
from ..base import ImportStatus

logger = logging.getLogger(__name__)


class SubjectRow(BaseModel):
    code: str
    name: str
    required_room_type: str

class ClassRow(BaseModel):
    name: str
    grade_level_name: str

class GradeLevelRow(BaseModel):
    name: str
    ordering: int

    @field_validator("ordering", mode="before")
    @classmethod
    def _coerce_ordering(cls, v: Any) -> int:
        try: return int(v)
        except Exception as exc: raise ValueError("ordering must be integer") from exc

class GradeSubjectRequirementRow(BaseModel):
    grade_level_name: str
    subject_code: str
    lessons_per_week: int


def upsert_subject(session: Session, row: SubjectRow) -> ImportStatus:
    existing = session.query(RoomType).filter(RoomType.name.ilike(row.required_room_type)).one_or_none()
    rt_id = existing.id if existing else session.scalar(insert(RoomType).values(name=row.required_room_type).returning(RoomType.id))
    
    stmt = insert(Subject).values(
        id=_deterministic_uuid(str(row.code)), code=row.code, name=row.name, required_room_type_id=rt_id
    ).on_conflict_do_update(index_elements=[Subject.code], set_=dict(name=row.name, required_room_type_id=rt_id))
    session.execute(stmt)
    return ImportStatus.imported

def upsert_class(session: Session, row: ClassRow) -> ImportStatus:
    stmt = select(GradeLevel.id).where(GradeLevel.name == row.grade_level_name)
    grade_id = session.execute(stmt).scalar() or session.scalar(insert(GradeLevel).values(id=_deterministic_uuid(str(row.grade_level_name)), name=row.grade_level_name, ordering=0).returning(GradeLevel.id))
    
    stmt = insert(Class).values(name=row.name, grade_level_id=grade_id).on_conflict_do_update(index_elements=[Class.name], set_=dict(grade_level_id=grade_id))
    session.execute(stmt)
    return ImportStatus.imported

def upsert_grade(session: Session, row: GradeLevelRow) -> ImportStatus:
    stmt = insert(GradeLevel).values(id=_deterministic_uuid(str(row.name)), name=row.name, ordering=row.ordering).on_conflict_do_update(index_elements=[GradeLevel.name], set_=dict(ordering=row.ordering))
    session.execute(stmt)
    return ImportStatus.imported

def upsert_requirement(session: Session, row: GradeSubjectRequirementRow) -> ImportStatus:
    g_id = session.scalar(select(GradeLevel.id).where(GradeLevel.name == row.grade_level_name))
    s_id = session.scalar(select(Subject.id).where(Subject.code == row.subject_code))
    if not g_id or not s_id: raise ValueError("Referenced grade or subject not found")
    
    stmt = insert(GradeSubjectRequirement).values(grade_level_id=g_id, subject_id=s_id, lessons_per_week=row.lessons_per_week).on_conflict_do_update(index_elements=[GradeSubjectRequirement.grade_level_id, GradeSubjectRequirement.subject_id], set_=dict(lessons_per_week=row.lessons_per_week))
    session.execute(stmt)
    return ImportStatus.imported