from .base import run_import, log_summary, ImportStatus, ImportHandler
from .handlers import facilities, academic, scheduling, staff


IMPORT_REGISTRY: dict[str, ImportHandler] = {
    "lesson_slots": ImportHandler(scheduling.LessonSlotRow, scheduling.upsert_lesson_slot),
    "rooms": ImportHandler(facilities.RoomRow, facilities.upsert),
    "subjects": ImportHandler(academic.SubjectRow, academic.upsert_subject),
    "grade_levels": ImportHandler(academic.GradeLevelRow, academic.upsert_grade),
    "teachers": ImportHandler(staff.TeacherImportRow, staff.upsert_teacher_full),
}

__all__ = ["run_import", "log_summary", "IMPORT_REGISTRY", "ImportStatus"]