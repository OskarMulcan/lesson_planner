# Lesson Planner

## Overview

The Lesson Planner is a Python-based backend system designed to manage and automate the complex process of scheduling school lessons. Built on top of PostgreSQL and utilizing a Genetic Algorithm for schedule generation, the system provides a robust database schema to track teachers, subjects, classrooms, and student classes.

It handles everything from strict constraint satisfaction (e.g., no double-booking) to rendering HTML/PNG visualizations of the final schedules.

## Project Structure

```text
.
├── .env
├── .env.example
├── .gitignore
├── .python_version
├── pyproject.toml
├── README.md
├── uv.lock
├── data
│   └── examples
│       └── .gitignore
└── src
    └── lesson_planner
        ├── cli/                 # Typer-based CLI commands
        ├── data_imports/        # CSV parsing and DB upsert logic
        ├── models/              # SQLAlchemy ORM models
        ├── scheduler/           # Genetic Algorithm and scheduling engine
        ├── visualization/       # HTML & PNG schedule rendering
        ├── config.py            # Pydantic settings management
        ├── database.py          # DB connection and session handling
        └── logging_setup.py     # Centralized logging configuration

```

## Prerequisites

* **Python:** 3.14 or later
* **Database:** PostgreSQL with the `btree_gist` extension installed
* **Package Manager:** [uv](https://github.com/astral-sh/uv)

## Setup

1. **Clone the repository.**

    ```bash
    git clone https://github.com/OskarMulcan/lesson_planner

    ```

2. **Install dependencies:**

    ```bash
    uv sync

    ```

3. **Configure the Environment:**

    Copy the example environment file and adjust the parameters:

    ```bash
    cp .env.example .env

    ```

    **Key `.env` variables:**

    * `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`: PostgreSQL credentials.
    * `ENVIRONMENT`: Set to `DEVELOPMENT` or `PRODUCTION`.
    * `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (Default: `INFO`).
    * `LOG_TO_FILE`: `1` to enable, `0` to disable.
    * `LOG_FILE_PATH`: Path for log outputs (Required if `LOG_TO_FILE=1`).

---

## Command Line Interface (CLI) Reference

The application is operated via a Typer-based CLI. You can override the default log level on any command by prefixing it with the `--log-level` flag (e.g., `uv run lesson-planner --log-level DEBUG db init`).

### 1. Database Management (`db`)

Manage your PostgreSQL schemas (`facilities`, `academic`, `staff`, `schedule`, `integration`) and tables.

* **Initialize the Database:** Creates all extensions and schemas.

    ```bash
    uv run lesson-planner db init

    ```

* **Clear Data / Drop Schemas:** Truncates all tables to clear data:

    ```bash
    uv run lesson-planner db drop

    ```

    To completely drop and recreate the schemas from scratch, use the `--reinit` flag:

    ```bash
    uv run lesson-planner db drop --reinit

    ```

### 2. Importing Data (`import`)

Import your school data via UTF-8 encoded, comma-delimited CSV files. **Order matters** due to foreign-key dependencies.

**Required Import Order & Commands:**

1. `lesson-slots` (Prerequisite for availability)
2. `grade-levels` (Prerequisite for classes)
3. `teachers` (Prerequisite for subjects/availability)
4. `subjects` (Prerequisite for requirements)
5. `rooms` (No dependencies)
6. `teacher-subjects`
7. `teacher-availability`
8. `classes` (Missing grade-levels are auto-created)
9. `requirements`

**Example Usage:**

```bash
uv run lesson-planner import lesson-slots data/examples/lesson_slots.csv
uv run lesson-planner import teachers data/examples/teachers.csv

```

**CSV Column Specifications:**

* **lesson_slots.csv:** `slot_number` (int), `start_time` (HH:MM), `end_time` (HH:MM)
* **teachers.csv:** `first_name`, `last_name`, `employment_date` (YYYY-MM-DD), `weekly_hours` (int)
* **teacher_subjects.csv:** `teacher_first_name`, `teacher_last_name`, `teacher_employment_date` (YYYY-MM-DD), `subject_code`
* **teacher_availability.csv:** `teacher_first_name`, `teacher_last_name`, `teacher_employment_date` (YYYY-MM-DD), `day_of_week`, `slot_number`
* **subjects.csv:** `code`, `name`, `required_room_type`
* **rooms.csv:** `number` (str), `floor` (int), `room_type`, `capacity` (int, optional)
* **grade_levels.csv:** `name`, `ordering` (int)
* **classes.csv:** `name`, `grade_level_name`
* **grade_subject_requirements.csv:** `grade_level_name`, `subject_code`, `lessons_per_week` (int)

### 3. Scheduling (`schedule`)

Run the Genetic Algorithm to automatically generate a schedule based on your database constraints.

* **Run the Scheduler:**

    ```bash
    uv run lesson-planner schedule run --name "Fall Term 2026"

    ```

**Algorithm Tuning Flags:**

* `--name`, `-n`: Name of the generated schedule (Required)
* `--population-size`: Size of the GA population (Default: 50)
* `--tournament-size`: Size of tournament selection (Default: 5)
* `--mutation-rate`: Probability of mutation (Default: 0.1)
* `--repair-every-n`: Generations between repairs (Default: 10)
* `--max-generations`: Max generations to run (Default: 100)
* `--fitness-threshold`: Target fitness to stop early (Default: 0.0)
* `--elite-size`: Number of top chromosomes to keep (Default: 1)
* `--active`: Set the generated schedule as the active one.

### 4. Visualization (`viz`)

Generate, view, and export visual representations of your schedules.

* **Generate Visualizations:** Creates HTML/PNG entries in the database for a specific schedule ID.

    ```bash
    uv run lesson-planner viz generate <SCHEDULE_UUID>

    ```

* **List Visualizations:** See what visual formats are available.

    ```bash
    uv run lesson-planner viz list <SCHEDULE_UUID> --dimension ROOM

    ```

    *Dimensions available:* `ROOM`, `CLASS`, `TEACHER`

* **Export to Disk:** Save HTML and PNG files to a local directory.

    ```bash
    uv run lesson-planner viz export <SCHEDULE_UUID> ./exports --dimension CLASS

    ```
