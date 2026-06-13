from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from .grid import ScheduleGrid


def render_png(grid: ScheduleGrid, dpi: int = 150) -> bytes:
    """Render a schedule grid as a PNG image.

    Uses the same day-as-column / slot-as-row layout as the HTML renderer:
    a matplotlib table with weekday column headers, slot-number-and-time
    row headers, and one cell per (day, slot).

    Args:
        grid: The day/slot grid for a single room, class, or teacher.
        dpi: Output resolution.

    Returns:
        PNG-encoded image bytes.
    """
    n_rows = len(grid.slots)
    n_cols = len(grid.days)

    fig_width = 1.6 + 2.0 * n_cols
    fig_height = 1.2 + 0.9 * n_rows

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis("off")
    ax.set_title(grid.label, fontsize=14, fontweight="bold", pad=16)

    col_labels = [day.value.title() for day in grid.days]
    row_labels = [f"{slot.slot_number}\n{slot.label}" for slot in grid.slots]

    cell_text: list[list[str]] = []
    for slot in grid.slots:
        line: list[str] = []
        for day in grid.days:
            cell = grid.cell(day, slot.id)
            line.append("\n".join(cell.lines) if cell else "")
        cell_text.append(line)

    table = ax.table(
        cellText=cell_text,
        rowLabels=row_labels,
        colLabels=col_labels,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1.0, 3.0)

    for (row, col), tbl_cell in table.get_celld().items():
        tbl_cell.set_edgecolor("#cbd2d9")
        if row == 0 or col == -1:
            tbl_cell.set_facecolor("#f5f7fa")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()