from __future__ import annotations
import logging
from typing import Any, Set, Dict, Tuple
from pydantic import BaseModel, field_validator
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, and_, tuple_

from ...models.academic import Subject, GradeLevel, Class, GradeSubjectRequirement
from ...models.facilities import RoomType
from ...models.base import _deterministic_uuid
from ..base import ImportStatus

logger = logging.getLogger(__name__)


class SubjectRow(BaseModel):
    code: str
    name: str
    required_room_type: str


class GradeLevelRow(BaseModel):
    name: str
    ordering: int
    classes: str = ""
    requirements: str = ""

    @field_validator("ordering", mode="before")
    @classmethod
    def _coerce_ordering(cls, v: Any) -> int:
        try:
            return int(v)
        except Exception as exc:
            raise ValueError("ordering must be an integer") from exc


def upsert_subject(session: Session, row: SubjectRow) -> ImportStatus:
    existing = session.query(RoomType).filter(RoomType.name.ilike(row.required_room_type)).one_or_none()
    if existing:
        rt_id = existing.id
    else:
        rt = RoomType(name=row.required_room_type)
        session.add(rt)
        session.flush()
        rt_id = rt.id
    
    stmt = insert(Subject).values(
        id=_deterministic_uuid(str(row.code)), code=row.code, name=row.name, required_room_type_id=rt_id
    ).on_conflict_do_update(index_elements=[Subject.code], set_=dict(name=row.name, required_room_type_id=rt_id))
    session.execute(stmt)
    return ImportStatus.imported


def upsert_grade(session: Session, row: GradeLevelRow) -> ImportStatus:
    g_id = _deterministic_uuid(str(row.name))
    stmt = insert(GradeLevel).values(
        id=g_id, 
        name=row.name, 
        ordering=row.ordering
    ).on_conflict_do_update(
        index_elements=[GradeLevel.name], 
        set_=dict(ordering=row.ordering)
    )
    session.execute(stmt)

    new_class_names = {c.strip() for c in row.classes.split(";") if c.strip()}
    existing_class_names = set(
        session.execute(select(Class.name).where(Class.grade_level_id == g_id)).scalars().all()
    )

    classes_to_add = new_class_names - existing_class_names
    classes_to_remove = existing_class_names - new_class_names

    if classes_to_remove:
        session.execute(
            delete(Class).where(
                and_(Class.grade_level_id == g_id, Class.name.in_(classes_to_remove))
            )
        )

    if classes_to_add:
        session.execute(
            insert(Class).values([
                {"id": _deterministic_uuid(name), "name": name, "grade_level_id": g_id}
                for name in classes_to_add
            ]).on_conflict_do_update(
                index_elements=[Class.name],
                set_=dict(grade_level_id=g_id)
            )
        )

    target_reqs: Dict[str, int] = {}
    if row.requirements.strip():
        for req_chunk in row.requirements.split(";"):
            req_chunk = req_chunk.strip()
            if not req_chunk or ":" not in req_chunk:
                continue
            code, count_str = req_chunk.split(":", 1)
            try:
                target_reqs[code.strip().upper()] = int(count_str.strip())
            except ValueError:
                logger.warning(f"Skipping malformed requirement count value: {req_chunk}")

    valid_subjects: Dict[str, Any] = {}
    if target_reqs:
        db_subjects = session.execute(
            select(Subject.id, Subject.code).where(Subject.code.in_(list(target_reqs.keys())))
        ).all()
        valid_subjects = {sub.code.upper(): sub.id for sub in db_subjects}

    incoming_req_map: Dict[Any, int] = {
        valid_subjects[code]: count for code, count in target_reqs.items() if code in valid_subjects
    }

    existing_reqs = session.execute(
        select(GradeSubjectRequirement.subject_id, GradeSubjectRequirement.lessons_per_week)
        .where(GradeSubjectRequirement.grade_level_id == g_id)
    ).all()
    existing_req_map: Dict[Any, int] = {r.subject_id: r.lessons_per_week for r in existing_reqs}

    incoming_ids = set(incoming_req_map.keys())
    existing_ids = set(existing_req_map.keys())

    reqs_to_remove = existing_ids - incoming_ids
    reqs_to_upsert = incoming_ids
    
    if reqs_to_remove:
        session.execute(
            delete(GradeSubjectRequirement).where(
                and_(
                    GradeSubjectRequirement.grade_level_id == g_id,
                    GradeSubjectRequirement.subject_id.in_(reqs_to_remove)
                )
            )
        )

    if reqs_to_upsert:
        stmt = insert(GradeSubjectRequirement).values([
            {
                "grade_level_id": g_id, 
                "subject_id": s_id, 
                "lessons_per_week": incoming_req_map[s_id]
            }
            for s_id in reqs_to_upsert
        ])
        
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=[GradeSubjectRequirement.grade_level_id, GradeSubjectRequirement.subject_id],
            set_=dict(lessons_per_week=stmt.excluded.lessons_per_week)
        )
        
        session.execute(upsert_stmt)

    return ImportStatus.imported