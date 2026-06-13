"""Generate a full-scale primary-school dataset into data/examples/.

8 grade levels x 2 classes (A/B) = 16 classes, ~17 subjects, 18 teachers,
19 rooms (16 general + 2 gym + 1 computer lab), 8 lesson slots/day x 5 days.
"""
from __future__ import annotations

import csv
from pathlib import Path

OUT = Path("data/examples")
OUT.mkdir(parents=True, exist_ok=True)

DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
AVAILABLE_SLOTS = [1, 2, 3, 4, 5, 6]

# --- subjects: code -> (name, required_room_type) --------------------------
SUBJECTS = {
    "POL": ("Polski", "general"),
    "MAT": ("Matematyka", "general"),
    "ANG": ("Angielski", "general"),
    "WF": ("Wychowanie fizyczne", "gym"),
    "MUZ": ("Muzyka", "general"),
    "PLA": ("Plastyka", "general"),
    "INF": ("Informatyka", "computer"),
    "REL": ("Religia", "general"),
    "TEC": ("Technika", "general"),
    "PRZ": ("Przyroda", "general"),
    "BIO": ("Biologia", "general"),
    "GEO": ("Geografia", "general"),
    "HIS": ("Historia", "general"),
    "CHE": ("Chemia", "general"),
    "FIZ": ("Fizyka", "general"),
    "WOS": ("Wiedza o spoleczenstwie", "general"),
    "EDB": ("Edukacja dla bezpieczenstwa", "general"),
}

# --- curriculum: grade (1-8) -> {subject_code: lessons_per_week} -----------
CURRICULUM = {
    1: {"POL": 5, "MAT": 4, "ANG": 2, "WF": 3, "MUZ": 1, "PLA": 1, "INF": 1, "REL": 2},
    2: {"POL": 5, "MAT": 4, "ANG": 2, "WF": 3, "MUZ": 1, "PLA": 1, "INF": 1, "REL": 2},
    3: {"POL": 5, "MAT": 4, "ANG": 2, "WF": 3, "MUZ": 1, "PLA": 1, "INF": 1, "REL": 2},
    4: {"POL": 5, "MAT": 4, "ANG": 3, "WF": 4, "MUZ": 1, "PLA": 1, "TEC": 1, "PRZ": 2, "HIS": 2, "INF": 1, "REL": 2},
    5: {"POL": 5, "MAT": 4, "ANG": 3, "WF": 4, "MUZ": 1, "PLA": 1, "TEC": 1, "BIO": 2, "GEO": 1, "HIS": 2, "INF": 1, "REL": 2},
    6: {"POL": 5, "MAT": 4, "ANG": 3, "WF": 4, "MUZ": 1, "PLA": 1, "TEC": 1, "BIO": 2, "GEO": 2, "HIS": 2, "INF": 1, "REL": 2},
    7: {"POL": 5, "MAT": 4, "ANG": 3, "WF": 4, "MUZ": 1, "PLA": 1, "BIO": 2, "GEO": 2, "HIS": 2, "CHE": 2, "FIZ": 2, "INF": 1, "REL": 2},
    8: {"POL": 5, "MAT": 4, "ANG": 3, "WF": 4, "BIO": 1, "GEO": 2, "HIS": 2, "CHE": 2, "FIZ": 2, "INF": 1, "WOS": 1, "EDB": 1, "REL": 2},
}

# --- teachers: (first, last, employment_date, weekly_hours, [subject_codes]) ---
TEACHERS = [
    ("Anna",     "Kowalska",     "2015-09-01", 22, ["POL", "REL"]),
    ("Maria",    "Nowakowska",   "2016-09-01", 22, ["POL", "REL"]),
    ("Piotr",    "Wisniewski",   "2014-09-01", 22, ["POL", "HIS", "EDB"]),
    ("Tomasz",   "Wojcik",       "2018-09-01", 22, ["POL", "HIS", "WOS"]),
    ("Katarzyna","Kowalczyk",    "2017-09-01", 22, ["MAT", "FIZ"]),
    ("Pawel",    "Kaminski",     "2013-09-01", 22, ["MAT", "CHE"]),
    ("Agnieszka","Lewandowska",  "2019-09-01", 22, ["MAT", "INF"]),
    ("Marek",    "Zielinski",    "2012-09-01", 22, ["MAT", "INF", "PRZ"]),
    ("Ewa",      "Szymanska",    "2015-09-01", 20, ["ANG"]),
    ("Jakub",    "Wozniak",      "2020-09-01", 20, ["ANG"]),
    ("Magdalena","Dabrowska",    "2016-09-01", 22, ["ANG", "GEO", "BIO"]),
    ("Lukasz",   "Kozlowski",    "2014-09-01", 20, ["WF"]),
    ("Adam",     "Jankowski",    "2017-09-01", 20, ["WF"]),
    ("Rafal",    "Mazur",        "2018-09-01", 22, ["WF", "TEC"]),
    ("Joanna",   "Krawczyk",     "2015-09-01", 18, ["MUZ", "PLA"]),
    ("Aleksandra","Piotrowska",  "2019-09-01", 20, ["MUZ", "PLA", "TEC"]),
    ("Krzysztof","Grabowski",    "2013-09-01", 20, ["BIO", "GEO", "PRZ"]),
    ("Monika",   "Pawlowska",    "2016-09-01", 18, ["CHE", "FIZ", "WOS", "EDB"]),
]

# --- rooms -------------------------------------------------------------------
GENERAL_ROOMS = [f"G{n:02d}" for n in range(1, 17)]
GYM_ROOMS = ["GYM1", "GYM2"]
COMPUTER_ROOMS = ["COMP1"]


def write_csv(filename: str, header: list[str], rows: list[list]) -> None:
    path = OUT / filename
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"wrote {path} ({len(rows)} rows)")


def main() -> None:
    # lesson_slots.csv - 8 slots/day
    slot_times = [
        ("08:00", "08:45"), ("08:55", "09:40"), ("09:50", "10:35"), ("10:45", "11:30"),
        ("11:40", "12:25"), ("12:35", "13:20"), ("13:30", "14:15"), ("14:25", "15:10"),
    ]
    write_csv(
        "lesson_slots.csv",
        ["slot_number", "start_time", "end_time"],
        [[i + 1, start, end] for i, (start, end) in enumerate(slot_times)],
    )

    # grade_levels.csv - G1..G8
    write_csv(
        "grade_levels.csv",
        ["name", "ordering"],
        [[f"G{g}", g] for g in range(1, 9)],
    )

    # classes.csv - 1A/1B .. 8A/8B
    write_csv(
        "classes.csv",
        ["name", "grade_level_name"],
        [[f"{g}{section}", f"G{g}"] for g in range(1, 9) for section in ("A", "B")],
    )

    # teachers.csv
    write_csv(
        "teachers.csv",
        ["first_name", "last_name", "employment_date", "weekly_hours"],
        [[t[0], t[1], t[2], t[3]] for t in TEACHERS],
    )

    # subjects.csv
    write_csv(
        "subjects.csv",
        ["code", "name", "required_room_type"],
        [[code, name, room_type] for code, (name, room_type) in SUBJECTS.items()],
    )

    # rooms.csv
    room_rows = []
    for number in GENERAL_ROOMS:
        room_rows.append([number, 1, "general", 28])
    for number in GYM_ROOMS:
        room_rows.append([number, 0, "gym", 40])
    for number in COMPUTER_ROOMS:
        room_rows.append([number, 1, "computer", 24])
    write_csv("rooms.csv", ["number", "floor", "room_type", "capacity"], room_rows)

    # teacher_subjects.csv
    ts_rows = []
    for first, last, date, _hours, subjects in TEACHERS:
        for code in subjects:
            ts_rows.append([first, last, date, code])
    write_csv(
        "teacher_subjects.csv",
        ["teacher_first_name", "teacher_last_name", "teacher_employment_date", "subject_code"],
        ts_rows,
    )

    # teacher_availability.csv - slots 1-6, all 5 days, every teacher
    ta_rows = []
    for first, last, date, _hours, _subjects in TEACHERS:
        for day in DAYS:
            for slot in AVAILABLE_SLOTS:
                ta_rows.append([first, last, date, day, slot])
    write_csv(
        "teacher_availability.csv",
        ["teacher_first_name", "teacher_last_name", "teacher_employment_date", "day_of_week", "slot_number"],
        ta_rows,
    )

    # grade_subject_requirements.csv
    req_rows = []
    for grade, subjects in CURRICULUM.items():
        for code, lessons in subjects.items():
            req_rows.append([f"G{grade}", code, lessons])
    write_csv(
        "grade_subject_requirements.csv",
        ["grade_level_name", "subject_code", "lessons_per_week"],
        req_rows,
    )

    # summary
    total_lessons_per_class = {g: sum(s.values()) for g, s in CURRICULUM.items()}
    total_lessons = sum(total_lessons_per_class.values()) * 2  # 2 classes/grade
    print("\n--- summary ---")
    for g, total in total_lessons_per_class.items():
        print(f"Grade {g}: {total} lessons/week/class (capacity 40)")
    print(f"Total lessons/week (whole school): {total_lessons}")
    print(f"Teachers: {len(TEACHERS)}, Rooms: {len(GENERAL_ROOMS) + len(GYM_ROOMS) + len(COMPUTER_ROOMS)}")


if __name__ == "__main__":
    main()