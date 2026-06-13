from .base import run_import, log_summary, ImportStatus, ImportHandler
from .handlers import facilities, academic, scheduling, staff


IMPORT_REGISTRY: dict[str, ImportHandler] = {
    "rooms": ImportHandler(facilities.RoomRow, facilities.upsert),
    "subjects": ImportHandler(academic.SubjectRow, academic.upsert_subject),
    "classes": ImportHandler(academic.ClassRow, academic.upsert_class),
    "grade_levels": ImportHandler(academic.GradeLevelRow, academic.upsert_grade),
    "requirements": ImportHandler(academic.GradeSubjectRequirementRow, academic.upsert_requirement),
    "teachers": ImportHandler(staff.TeacherRow, staff.upsert_teacher),
    "teacher_subjects": ImportHandler(staff.TeacherSubjectRow, staff.upsert_teacher_subject),
    "teacher_availability": ImportHandler(staff.TeacherAvailabilityRow, staff.upsert_teacher_availability),
    "lesson_slots": ImportHandler(scheduling.LessonSlotRow, scheduling.upsert_lesson_slot),
}

__all__ = ["run_import", "log_summary", "IMPORT_REGISTRY", "ImportStatus"]