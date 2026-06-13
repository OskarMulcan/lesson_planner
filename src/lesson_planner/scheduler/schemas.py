from __future__ import annotations

from uuid import UUID
from dataclasses import dataclass, field
from collections import defaultdict

from lesson_planner.models import (
    DayOfWeek, 
    LessonSlot,
    Room,
    Subject,
    Class,
    GradeSubjectRequirement,
    TeacherAvailability,
    TeacherSubject,
)


@dataclass
class SchedulingContext:
    # --- requirement: class_id → subject_id → lessons/week -------------------
    required_lessons: dict[UUID, dict[UUID, int]] = field(default_factory=dict)

    # --- availability: teacher_id → frozenset{(day, slot_order)} -------------
    teacher_available: dict[UUID, frozenset[tuple[DayOfWeek, UUID]]] = field(default_factory=dict)

    # --- eligible teachers per subject ---------------------------------------
    subject_teachers: dict[UUID, list[UUID]] = field(default_factory=dict)

    # --- eligible rooms per subject (pre-filtered by required room type) -----
    subject_rooms: dict[UUID, list[UUID]] = field(default_factory=dict)

    # --- all (day, slot_order) pairs for random gene init / mutation ---------
    all_day_slots: list[tuple[DayOfWeek, UUID]] = field(default_factory=list)


def build_scheduling_context(session) -> SchedulingContext:
    ctx = SchedulingContext()

    ordered_slots: list[UUID] = [
        row.id
        for row in session.query(LessonSlot.id).order_by(LessonSlot.slot_number).all()
    ]
    ctx.all_day_slots = [
        (day, order)
        for day in DayOfWeek
        for order in ordered_slots
    ]

    rooms_by_type: dict[UUID, list[UUID]] = defaultdict(list)
    for row in session.query(Room.id, Room.room_type_id).all():
        rooms_by_type[row.room_type_id].append(row.id)

    for row in session.query(Subject.id, Subject.required_room_type_id).all():
        ctx.subject_rooms[row.id] = rooms_by_type.get(row.required_room_type_id, [])

    classes_by_grade: dict[UUID, list[UUID]] = defaultdict(list)
    for row in session.query(Class.id, Class.grade_level_id).all():
        classes_by_grade[row.grade_level_id].append(row.id)

    temp_required_subjects: dict[UUID, dict[UUID, int]] = defaultdict(dict)
    for row in session.query(
        GradeSubjectRequirement.grade_level_id,
        GradeSubjectRequirement.subject_id,
        GradeSubjectRequirement.lessons_per_week,
    ).all():
        for class_id in classes_by_grade[row.grade_level_id]:
            temp_required_subjects[class_id][row.subject_id] = int(row.lessons_per_week)
    ctx.required_lessons = dict(temp_required_subjects)

    temp_teacher_availability: dict[UUID, set[tuple[DayOfWeek, UUID]]] = defaultdict(set)
    for row in session.query(
        TeacherAvailability.teacher_id,
        TeacherAvailability.day_of_week,
        TeacherAvailability.slot_id,
    ).all():
        temp_teacher_availability[row.teacher_id].add((row.day_of_week, row.slot_id))
    ctx.teacher_available = {tid: frozenset(slots) for tid, slots in temp_teacher_availability.items()}


    temp_subject_teachers: dict[UUID, list[UUID]] = defaultdict(list)
    for row in session.query(TeacherSubject.subject_id, TeacherSubject.teacher_id).all():
        temp_subject_teachers[row.subject_id].append(row.teacher_id)
    ctx.subject_teachers = dict(temp_subject_teachers)

    return ctx