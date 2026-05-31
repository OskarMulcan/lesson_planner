from __future__ import annotations

import logging
import typer
from pathlib import Path

from lesson_planner.logging_setup import configure_logging
from lesson_planner.database import init_db

app = typer.Typer()

# Sub-apps
import_app = typer.Typer()
db_app = typer.Typer()
app.add_typer(db_app, name="db")
app.add_typer(import_app, name="import")


def _log_level_callback(ctx: typer.Context, value: str) -> str:
    if value:
        configure_logging(value)
    return value


@app.callback(invoke_without_command=True)
def main(
    log_level: str = typer.Option(
        None,
        "--log-level",
        callback=_log_level_callback,
        help="Override log level",
    ),
) -> None:
    """Top level CLI for lesson planner."""
    return None


@db_app.command()
def init() -> None:
    """Initialize the database schema."""
    logger = logging.getLogger(__name__)
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as exc:
        logger.exception("Database initialization failed: %s", exc)
        raise typer.Exit(code=1)


# Import commands
@import_app.command("lesson-slots")
def import_lesson_slots(path: Path) -> None:
    """Import lesson slots from CSV.

    CSV columns: slot_number,start_time,end_time
    """
    configure_logging()
    from lesson_planner.database import get_session
    from lesson_planner.imports.lesson_slots import LessonSlotRow, upsert as upsert_fn
    from lesson_planner.imports.base import run_import, log_summary

    with get_session() as session:
        results = run_import(session, path, "lesson_slots", LessonSlotRow, upsert_fn)
        log_summary(results, "lesson_slots")
        failed = any(r.status.value == "failed" for r in results)
        raise typer.Exit(code=1 if failed else 0)


@import_app.command("teachers")
def import_teachers(path: Path) -> None:
    """Import teachers from CSV.

    CSV columns: first_name,last_name,employment_date,weekly_hours
    """
    configure_logging()
    from lesson_planner.database import get_session
    from lesson_planner.imports.teachers import TeacherRow, upsert as upsert_fn
    from lesson_planner.imports.base import run_import, log_summary

    with get_session() as session:
        results = run_import(session, path, "teachers", TeacherRow, upsert_fn)
        log_summary(results, "teachers")
        failed = any(r.status.value == "failed" for r in results)
        raise typer.Exit(code=1 if failed else 0)


@import_app.command("teacher-subjects")
def import_teacher_subjects(path: Path) -> None:
    """Import teacher-subject assignments from CSV.

    CSV columns: teacher_first_name,teacher_last_name,teacher_employment_date,subject_code
    """
    configure_logging()
    from lesson_planner.database import get_session
    from lesson_planner.imports.teacher_subjects import TeacherSubjectRow, upsert as upsert_fn
    from lesson_planner.imports.base import run_import, log_summary

    with get_session() as session:
        results = run_import(session, path, "teacher_subjects", TeacherSubjectRow, upsert_fn)
        log_summary(results, "teacher_subjects")
        failed = any(r.status.value == "failed" for r in results)
        raise typer.Exit(code=1 if failed else 0)


@import_app.command("teacher-availability")
def import_teacher_availability(path: Path) -> None:
    """Import teacher availability from CSV.

    CSV columns: teacher_first_name,teacher_last_name,teacher_employment_date,day_of_week,slot_number
    """
    configure_logging()
    from lesson_planner.database import get_session
    from lesson_planner.imports.teacher_availability import TeacherAvailabilityRow, upsert as upsert_fn
    from lesson_planner.imports.base import run_import, log_summary

    with get_session() as session:
        results = run_import(session, path, "teacher_availability", TeacherAvailabilityRow, upsert_fn)
        log_summary(results, "teacher_availability")
        failed = any(r.status.value == "failed" for r in results)
        raise typer.Exit(code=1 if failed else 0)


@import_app.command("subjects")
def import_subjects(path: Path) -> None:
    """Import subjects from CSV.

    CSV columns: code,name,required_room_type
    """
    configure_logging()
    from lesson_planner.database import get_session
    from lesson_planner.imports.subjects import SubjectRow, upsert as upsert_fn
    from lesson_planner.imports.base import run_import, log_summary

    with get_session() as session:
        results = run_import(session, path, "subjects", SubjectRow, upsert_fn)
        log_summary(results, "subjects")
        failed = any(r.status.value == "failed" for r in results)
        raise typer.Exit(code=1 if failed else 0)


@import_app.command("rooms")
def import_rooms(path: Path) -> None:
    """Import rooms from CSV.

    CSV columns: number,floor,room_type,capacity
    """
    configure_logging()
    from lesson_planner.database import get_session
    from lesson_planner.imports.rooms import RoomRow, upsert as upsert_fn
    from lesson_planner.imports.base import run_import, log_summary

    with get_session() as session:
        results = run_import(session, path, "rooms", RoomRow, upsert_fn)
        log_summary(results, "rooms")
        failed = any(r.status.value == "failed" for r in results)
        raise typer.Exit(code=1 if failed else 0)


@import_app.command("grade-levels")
def import_grade_levels(path: Path) -> None:
    """Import grade levels from CSV.

    CSV columns: name,ordering
    """
    configure_logging()
    from lesson_planner.database import get_session
    from lesson_planner.imports.grade_levels import GradeLevelRow, upsert as upsert_fn
    from lesson_planner.imports.base import run_import, log_summary

    with get_session() as session:
        results = run_import(session, path, "grade_levels", GradeLevelRow, upsert_fn)
        log_summary(results, "grade_levels")
        failed = any(r.status.value == "failed" for r in results)
        raise typer.Exit(code=1 if failed else 0)


@import_app.command("classes")
def import_classes(path: Path) -> None:
    """Import classes from CSV.

    CSV columns: name,grade_level_name
    """
    configure_logging()
    from lesson_planner.database import get_session
    from lesson_planner.imports.classes import ClassRow, upsert as upsert_fn
    from lesson_planner.imports.base import run_import, log_summary

    with get_session() as session:
        results = run_import(session, path, "classes", ClassRow, upsert_fn)
        log_summary(results, "classes")
        failed = any(r.status.value == "failed" for r in results)
        raise typer.Exit(code=1 if failed else 0)


@import_app.command("requirements")
def import_requirements(path: Path) -> None:
    """Import grade subject requirements from CSV.

    CSV columns: grade_level_name,subject_code,lessons_per_week
    """
    configure_logging()
    from lesson_planner.database import get_session
    from lesson_planner.imports.grade_subject_requirements import GradeSubjectRequirementRow, upsert as upsert_fn
    from lesson_planner.imports.base import run_import, log_summary

    with get_session() as session:
        results = run_import(session, path, "grade_subject_requirements", GradeSubjectRequirementRow, upsert_fn)
        log_summary(results, "grade_subject_requirements")
        failed = any(r.status.value == "failed" for r in results)
        raise typer.Exit(code=1 if failed else 0)
