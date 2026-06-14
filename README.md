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

* **Initialize the Database:** Creates required extensions, sets up the application schemas, and maps out all structural data tables.

    ```bash
    uv run lesson-planner db init
    ```

* **Clear Table Data:** Truncates all tables across all application schemas. This empties all data records and resets auto-incrementing identities while preserving your schema structure.

    ```bash
    uv run lesson-planner db clear
    ```

* **Drop Schemas Completely:** Permanently deletes the application schemas along with every table, structural constraint, and row of data inside them.

    ```bash
    uv run lesson-planner db drop
    ```

    To completely destroy all current configurations and immediately re-initialize clean, empty schemas and tables for a fresh workspace, use the `--reinit` flag:

    ```bash
    uv run lesson-planner db drop --reinit
    ```

### 2. Importing Data (`import`)

Import your school data via UTF-8 encoded, comma-delimited CSV files. **Order matters** due to foreign-key dependencies.

**Required Import Order & Commands:**

1. `lesson-slots`
2. `rooms`
3. `subjects`
4. `grade-levels` *(Consolidates classes and subject lesson requirements)*
5. `teachers` *(Consolidates subjects taught and weekly scheduling windows)*

**Example Usage:**

```bash
uv run lesson-planner import lesson-slots data/examples/lesson_slots.csv
uv run lesson-planner import grade-levels data/examples/grade_levels.csv
uv run lesson-planner import teachers data/examples/teachers.csv

```

**CSV Column Specifications:**

* **`lesson_slots.csv`:**
  * `slot_number` (int) - Sequential ID of the period.
  * `start_time` (time) - Formatted strictly as `HH:MM` (e.g., `08:00`).
  * `end_time` (time) - Formatted strictly as `HH:MM` (e.g., `08:45`).

* **`rooms.csv`:**
  * `number` (str) - Unique classroom identifier/room number.
  * `floor` (int) - Building level.
  * `room_type` (str) - Must match valid facility constraints (`STANDARD`, `LAB`, `COMPUTER_LAB`, `MUSIC`, `GYM`).
  * `capacity` (int, optional) - Maximum student capacity.

* **`subjects.csv`:**
  * `code` (str) - Short alphanumeric code (e.g., `MAT`, `POL`).
  * `name` (str) - Full subject title (e.g., `Mathematics`).
  * `required_room_type` (str) - Maps to required room types (creates the type dynamically if it doesn't exist).

* **`grade_levels.csv`:**
  * `name` (str) - Unique name of the grade layer (e.g., `Year IV`).
  * `ordering` (int) - Sorting priority index for scheduling structures.
  * `classes` (str) - Semicolon-separated names of the individual class sections to spawn or sync (e.g., `Year IVa;Year IVb;Year IVc`).
  * `requirements` (str) - Semicolon-separated pairs of `SUBJECT_CODE:HOURS` defining the weekly timeline requirements (e.g., `POL:5;ANG:3;MAT:4;PE:4`). Non-existent subject codes are automatically skipped.

* **`teachers.csv`:**
  * `first_name` (str) - Teacher's first name.
  * `last_name` (str) - Teacher's surname.
  * `employment_date` (date) - Date formatted as `YYYY-MM-DD`. Combined with names to form a unique composite key.
  * `weekly_hours` (int) - Total target contract hours per week.
  * `subjects` (str) - Semicolon-separated subject codes this teacher is qualified to instruct (e.g., `GEO;BIO;CHEM`).
  * `availability` (str) - Semicolon-separated day-and-time boundaries defining when a teacher can be scheduled. Days must use uppercase names, and times must be strictly `HH:MM` (e.g., `MONDAY:08:00-14:25;WEDNESDAY:08:00-11:40`). Any slot fully resting inside these custom windows will be flagged as available.

Here is the updated section for your README, including the new `check` command for diagnosing generated schedules:

---

### 3. Scheduling (`schedule`)

Run the Genetic Algorithm to automatically generate a schedule based on your database constraints, or verify existing schedules for violations.

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
  * `--final-repair-attempts`: Number of final repair attempts per candidate (Default: 25)
  * `--final-candidates`: Number of final candidates to choose the best schedule from (Default: 5)
  * `--active`: Set the generated schedule as the active one.

* **Check a Schedule for Violations:**

    Evaluate an existing schedule against the master constraint registry. This will output a diagnostic report listing the overall penalty score and any active rule violations.

    ```bash
    uv run lesson-planner schedule check <SCHEDULE_UUID>
    ```

    *Replace `<SCHEDULE_UUID>` with the actual UUID returned when the schedule was successfully saved.*

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
