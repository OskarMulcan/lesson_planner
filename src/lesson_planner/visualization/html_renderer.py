from __future__ import annotations

from html import escape

from .grid import ScheduleGrid

_CSS = """
body { font-family: Arial, Helvetica, sans-serif; margin: 24px; color: #1f2933; }
h1 { font-size: 20px; margin-bottom: 12px; }
table { border-collapse: collapse; width: 100%; table-layout: fixed; }
th, td { border: 1px solid #cbd2d9; padding: 6px 8px; vertical-align: top; text-align: left; }
thead th { background: #f5f7fa; text-align: center; font-weight: 600; }
th.slot { background: #f5f7fa; text-align: center; white-space: nowrap; width: 90px; }
th.slot .time { display: block; font-size: 11px; font-weight: normal; color: #616e7c; }
td { height: 56px; }
.title { font-weight: 600; }
.subtitle { font-size: 12px; color: #3e4c59; }
.extra { font-size: 11px; color: #7b8794; }
""".strip()


def render_html(grid: ScheduleGrid) -> str:
    """Render a schedule grid as a standalone HTML document.

    Days run across the columns (in fixed weekday order), lesson slots run
    down the rows (in slot_number order), with slot numbers and start/end
    times shown in the leftmost column.

    Args:
        grid: The day/slot grid for a single room, class, or teacher.

    Returns:
        A complete, self-contained HTML document as a string.
    """
    header_cells = "".join(f"<th>{escape(day.value.title())}</th>" for day in grid.days)

    body_rows: list[str] = []
    for slot in grid.slots:
        row_cells: list[str] = []
        for day in grid.days:
            cell = grid.cell(day, slot.id)
            if cell is None:
                row_cells.append("<td></td>")
                continue

            parts = [f'<div class="title">{escape(cell.title)}</div>']
            if cell.subtitle:
                parts.append(f'<div class="subtitle">{escape(cell.subtitle)}</div>')
            if cell.extra:
                parts.append(f'<div class="extra">{escape(cell.extra)}</div>')
            row_cells.append(f"<td>{''.join(parts)}</td>")

        slot_header = (
            f'<th class="slot">{slot.slot_number}'
            f'<span class="time">{escape(slot.label)}</span></th>'
        )
        body_rows.append(f"<tr>{slot_header}{''.join(row_cells)}</tr>")

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"<title>{escape(grid.label)}</title>\n"
        f"<style>{_CSS}</style>\n"
        "</head>\n"
        "<body>\n"
        f"<h1>{escape(grid.label)}</h1>\n"
        "<table>\n"
        f"<thead><tr><th></th>{header_cells}</tr></thead>\n"
        f"<tbody>{''.join(body_rows)}</tbody>\n"
        "</table>\n"
        "</body>\n"
        "</html>\n"
    )