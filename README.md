# Lesson Planner

## Overview

The Lesson Planner is a Python-based backend system designed to manage and automate the
scheduling of lessons in a school. It provides a comprehensive database schema to track
teachers, subjects, lesson slots, classrooms, and student classes. The system supports
importing data from CSV files and lays the foundation for algorithmic scheduling and
constraint satisfaction features.

## Prerequisites

- Python 3.14 or later
- PostgreSQL with the btree_gist extension
- uv package manager (https://github.com/astral-sh/uv)

## Setup

1. Clone or download the lesson planner repository.

2. Install dependencies:

        uv sync

3. Create a .env file in the project root directory by copying from .env.example:

        cp .env.example .env

4. Edit .env to configure your PostgreSQL connection parameters:

   - DB_HOST: PostgreSQL server hostname (default: localhost)
   - DB_PORT: PostgreSQL server port (default: 5432)
   - DB_NAME: Name of the lesson planner database
   - DB_USER: PostgreSQL user with access to the database
   - DB_PASSWORD: PostgreSQL password for the user

## Database Initialization

Initialize the database schema by running:

    uv run lesson-planner db init

This command creates all necessary tables including RoomType, LessonSlot, Room, Teacher,
Subject, GradeLevel, Class, GradeSubjectRequirement, TeacherSubject, TeacherAvailability,
Schedule, ScheduleEntry, and ImportStaging.

## Importing Data

Import data using the import command group. CSV files must be comma-delimited, UTF-8
encoded, with a header row. Import commands follow a specific order due to foreign key
dependencies.

### Required Import Order

1. lesson-slots (prerequisite for teacher-availability)
2. grade-levels (prerequisite for classes)
3. teachers (prerequisite for teacher-subjects and teacher-availability)
4. subjects (prerequisite for teacher-subjects and grade-subject-requirements)
5. rooms (no dependencies)
6. teacher-subjects (requires teachers and subjects)
7. teacher-availability (requires teachers and lesson-slots)
8. classes (requires grade-levels; missing grade-levels are auto-created with ordering=0)
9. requirements (requires grade-levels and subjects)

### Example Usage

    uv run lesson-planner import lesson-slots data/examples/lesson_slots.csv
    uv run lesson-planner import grade-levels data/examples/grade_levels.csv
    uv run lesson-planner import teachers data/examples/teachers.csv
    uv run lesson-planner import subjects data/examples/subjects.csv
    uv run lesson-planner import rooms data/examples/rooms.csv
    uv run lesson-planner import teacher-subjects data/examples/teacher_subjects.csv
    uv run lesson-planner import teacher-availability data/examples/teacher_availability.csv
    uv run lesson-planner import classes data/examples/classes.csv
    uv run lesson-planner import requirements data/examples/grade_subject_requirements.csv

### CSV Column Specifications

**lesson_slots.csv**

    slot_number (integer), start_time (HH:MM), end_time (HH:MM)

**teachers.csv**

    first_name, last_name, employment_date (YYYY-MM-DD), weekly_hours (integer)

**teacher_subjects.csv**

    teacher_first_name, teacher_last_name, teacher_employment_date (YYYY-MM-DD), subject_code

**teacher_availability.csv**

    teacher_first_name, teacher_last_name, teacher_employment_date (YYYY-MM-DD), day_of_week, slot_number

**subjects.csv**

    code, name, required_room_type

**rooms.csv**

    number (string), floor (integer), room_type, capacity (integer, optional)

**grade_levels.csv**

    name, ordering (integer)

**classes.csv**

    name, grade_level_name

**grade_subject_requirements.csv**

    grade_level_name, subject_code, lessons_per_week (integer)

## Logging Configuration

Configure logging via environment variables in .env:

- LOG_LEVEL: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL; default: INFO)
- LOG_TO_FILE: Enable file logging (0 = disabled, 1 = enabled; default: 0)
- LOG_FILE_PATH: Path to log file (required when LOG_TO_FILE = 1)

Override the log level at runtime with the --log-level option:

    uv run lesson-planner --log-level DEBUG import lesson-slots data/examples/lesson_slots.csv

## Project Structure

    lesson-planner/
      src/
        lesson_planner/
          __init__.py                        Package init, exports settings and configure_logging
          config.py                          Settings and configuration management
          logging_setup.py                   Logging configuration
          database.py                        Database engine and session utilities
          models.py                          SQLAlchemy ORM models and schema definition
          cli/
            __init__.py                      CLI package init, exports app
            main.py                          Typer CLI application and commands
          imports/
            __init__.py                      Import module exports
            base.py                          Base import functions and utilities
            lesson_slots.py                  Lesson slot CSV import
            teachers.py                      Teacher CSV import
            teacher_subjects.py              Teacher-subject assignment import
            teacher_availability.py          Teacher availability import
            subjects.py                      Subject CSV import
            rooms.py                         Room CSV import
            grade_levels.py                  Grade level CSV import
            classes.py                       Class CSV import
            grade_subject_requirements.py    Grade subject requirement import
      data/
        examples/
          lesson_slots.csv                   Example lesson slots data
          teachers.csv                       Example teachers data
          teacher_subjects.csv               Example teacher-subject assignments
          teacher_availability.csv           Example teacher availability
          subjects.csv                       Example subjects data
          rooms.csv                          Example rooms data
          grade_levels.csv                   Example grade levels data
          classes.csv                        Example classes data
          grade_subject_requirements.csv     Example grade-subject requirements
      .env.example                           Environment configuration template
      .env                                   Local environment configuration (not in version control)
      pyproject.toml                         Project metadata and dependencies
      README.md                              This file