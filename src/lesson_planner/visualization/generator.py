from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from lesson_planner.models import DayOfWeek, LessonSlot, Schedule, ScheduleEntry, ScheduleVisualization, VisualizationDimension

from .grid import GridCell, ScheduleGrid, SlotInfo
from .html_renderer import render_html
from .png_renderer import render_png


def _load_slots(session: Session) -> list[SlotInfo]:
    """Load all lesson slots, ordered by slot_number, as grid rows."""
    rows = session.query(LessonSlot).order_by(LessonSlot.slot_number).all()
    return [
        SlotInfo(
            id=row.id,
            slot_number=row.slot_number,
            start_time=row.start_time,
            end_time=row.end_time,
        )
        for row in rows
    ]


def _load_entries(session: Session, schedule_id: UUID) -> list[ScheduleEntry]:
    """Load fully-assigned entries for a schedule.

    Only entries with every field populated (class, subject, teacher, room,
    day, slot) can be placed on a grid; partial/placeholder entries are
    skipped here.
    """
    return (
        session.query(ScheduleEntry)
        .filter(
            ScheduleEntry.schedule_id == schedule_id,
            ScheduleEntry.class_id.isnot(None),
            ScheduleEntry.subject_id.isnot(None),
            ScheduleEntry.teacher_id.isnot(None),
            ScheduleEntry.room_id.isnot(None),
            ScheduleEntry.day_of_week.isnot(None),
            ScheduleEntry.slot_id.isnot(None),
        )
        .all()
    )


def _build_grids(
    entries: list[ScheduleEntry],
    slots: list[SlotInfo],
    days: list[DayOfWeek],
) -> dict[VisualizationDimension, dict[UUID, ScheduleGrid]]:
    """Build one ScheduleGrid per (dimension, entity) pair from entries.

    For each entry, place a cell into the room's grid, the class's grid, and
    the teacher's grid simultaneously, each showing the other two dimensions
    as context.
    """
    grids: dict[VisualizationDimension, dict[UUID, ScheduleGrid]] = {
        dimension: {} for dimension in VisualizationDimension
    }

    def _grid_for(dimension: VisualizationDimension, entity_id: UUID, label: str) -> ScheduleGrid:
        bucket = grids[dimension]
        grid = bucket.get(entity_id)
        if grid is None:
            grid = ScheduleGrid(
                dimension=dimension,
                dimension_id=entity_id,
                label=label,
                days=days,
                slots=slots,
            )
            bucket[entity_id] = grid
        return grid

    for entry in entries:
        key = (entry.day_of_week, entry.slot_id)
        teacher_name = f"{entry.teacher.first_name} {entry.teacher.last_name}"

        room_grid = _grid_for(VisualizationDimension.ROOM, entry.room_id, entry.room.number)
        room_grid.cells[key] = GridCell(
            title=entry.klass.name,
            subtitle=entry.subject.name,
            extra=teacher_name,
        )

        class_grid = _grid_for(VisualizationDimension.CLASS, entry.class_id, entry.klass.name)
        class_grid.cells[key] = GridCell(
            title=entry.subject.name,
            subtitle=teacher_name,
            extra=f"Room {entry.room.number}",
        )

        teacher_grid = _grid_for(VisualizationDimension.TEACHER, entry.teacher_id, teacher_name)
        teacher_grid.cells[key] = GridCell(
            title=entry.klass.name,
            subtitle=entry.subject.name,
            extra=f"Room {entry.room.number}",
        )

    return grids


def generate_visualizations_for_schedule(
    session: Session, schedule_id: UUID
) -> list[ScheduleVisualization]:
    """Generate and persist room/class/teacher visualizations for a schedule.

    Reads schedule entries and lesson slots from the database, builds a
    fixed day/slot grid for every room, class, and teacher that appears in
    the schedule, renders each grid to HTML and PNG, and upserts the result
    into the schedule_visualizations table (one row per
    schedule/dimension/entity, overwritten on regeneration).

    Args:
        session: Active SQLAlchemy session. Caller is responsible for
            transaction scope; this function commits once at the end.
        schedule_id: The schedule to visualize. Must already exist with its
            entries fully populated (the GA + persistence step).

    Returns:
        The list of persisted ScheduleVisualization rows (one per room,
        class, and teacher present in the schedule).

    Raises:
        ValueError: If the schedule does not exist, or no lesson slots are
            configured.
    """
    schedule = session.get(Schedule, schedule_id)
    if schedule is None:
        raise ValueError(f"Schedule {schedule_id} not found")

    slots = _load_slots(session)
    if not slots:
        raise ValueError("No lesson slots configured; cannot build a schedule grid")

    entries = _load_entries(session, schedule_id)
    days = list(DayOfWeek)

    grids = _build_grids(entries, slots, days)

    persisted: list[ScheduleVisualization] = []
    for dimension, entities in grids.items():
        for dimension_id, grid in entities.items():
            viz = (
                session.query(ScheduleVisualization)
                .filter_by(schedule_id=schedule_id, dimension=dimension, dimension_id=dimension_id)
                .one_or_none()
            )
            if viz is None:
                viz = ScheduleVisualization(
                    schedule_id=schedule_id,
                    dimension=dimension,
                    dimension_id=dimension_id,
                )
                session.add(viz)

            viz.label = grid.label
            viz.html_content = render_html(grid)
            viz.png_content = render_png(grid)
            persisted.append(viz)

    session.commit()
    return persisted


def get_visualization(
    session: Session,
    schedule_id: UUID,
    dimension: VisualizationDimension,
    dimension_id: UUID,
) -> ScheduleVisualization | None:
    """Fetch a single persisted visualization, or None if not generated yet."""
    return (
        session.query(ScheduleVisualization)
        .filter_by(schedule_id=schedule_id, dimension=dimension, dimension_id=dimension_id)
        .one_or_none()
    )


def list_visualizations(
    session: Session,
    schedule_id: UUID,
    dimension: VisualizationDimension | None = None,
) -> list[ScheduleVisualization]:
    """List persisted visualizations for a schedule, optionally filtered by dimension."""
    query = session.query(ScheduleVisualization).filter_by(schedule_id=schedule_id)
    if dimension is not None:
        query = query.filter_by(dimension=dimension)
    return query.order_by(ScheduleVisualization.dimension, ScheduleVisualization.label).all()


def export_visualization(
    viz: ScheduleVisualization, output_dir: Path
) -> tuple[Path | None, Path | None]:
    """Write a single visualization's HTML and PNG content to disk.

    Args:
        viz: A persisted ScheduleVisualization row.
        output_dir: Directory to write files into; created if missing.

    Returns:
        A tuple of (html_path, png_path). Either element is None if that
        content was not stored for this row.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = f"{viz.dimension.value.lower()}_{viz.label}".replace(" ", "_").replace("/", "-")

    html_path: Path | None = None
    if viz.html_content:
        html_path = output_dir / f"{slug}.html"
        html_path.write_text(viz.html_content, encoding="utf-8")

    png_path: Path | None = None
    if viz.png_content:
        png_path = output_dir / f"{slug}.png"
        png_path.write_bytes(viz.png_content)

    return html_path, png_path


def export_all_visualizations(
    session: Session, schedule_id: UUID, output_dir: Path
) -> list[tuple[Path | None, Path | None]]:
    """Export every persisted visualization for a schedule to disk."""
    return [export_visualization(viz, output_dir) for viz in list_visualizations(session, schedule_id)]