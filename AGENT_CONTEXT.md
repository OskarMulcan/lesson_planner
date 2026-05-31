# Agent Context: Pass 1

## Setup and Dependencies
- alembic: >=1.18.4 (from pyproject.toml)
- psycopg: >=3.3.4 (from pyproject.toml)
- pydantic: >=2.13.4 (from pyproject.toml)
- pydantic-settings: >=2.14.1 (from pyproject.toml)
- python-dotenv: >=1.2.2 (from pyproject.toml)
- sqlalchemy: >=2.0.50 (from pyproject.toml)
- typer: >=0.26.4 (from pyproject.toml)

## pyproject.toml
- Changed the project script entry from
  `lesson-planner = "lesson_planner:main"` to
  `lesson-planner = "lesson_planner.cli.main:app"` to point the CLI entry
  point at the Typer app created in src/lesson_planner/cli/main.py.

## config.py
- No deviations from the specification except implementation details:
  - Used pydantic-settings BaseSettings and python-dotenv.load_dotenv() to load .env.
  - LOG_TO_FILE is stored as int and a `log_to_file` property converts it to bool.
  - database_url property URL-encodes user and password using urllib.parse.quote_plus.
  - Field validation implemented via pydantic field_validator and model_validator.

## logging_setup.py
- Decisions and deviations:
  - Implemented idempotent configuration using module-level state variables.
  - The function configures the root logger so that all module loggers (logging.getLogger(__name__)) inherit handlers.
  - Formatters: development uses a human readable formatter; production uses a single-line
    key=value style formatter as requested.
  - When LOG_TO_FILE is enabled but LOG_FILE_PATH is missing or parent directory cannot be
    created, a WARNING is logged and file handler is skipped.

## database.py
- Decisions and deviations:
  - Engine is created with create_engine(settings.database_url, future=True).
  - SessionLocal is sessionmaker bound to engine with expire_on_commit=False.
  - get_session is a contextmanager that yields a Session and performs commit/rollback.
  - init_db executes `CREATE EXTENSION IF NOT EXISTS btree_gist` then calls Base.metadata.create_all.
  - Any SQLAlchemyError is logged as a warning; unexpected exceptions are also logged.

## models.py
- General
  - Base is declarative_base().
  - LESSON_PLANNER_NS is set to a fixed uuid4 value: 7f9c5a3c-e4f2-4c95-8e25-2a1f4b7d3c9a.
  - Deterministic UUIDs are generated via uuid.uuid5(LESSON_PLANNER_NS, "|".join(parts)).
  - Random UUID primary keys use default=uuid.uuid4 and server_default=text("gen_random_uuid()").
  - PostgreSQL native enums are used via SAEnum(..., native_enum=True).
  - JSON column for ImportStaging uses SQLAlchemy JSON type (not JSONB). This choice is
    pragmatic; converting to JSONB can be done in a later pass or via migrations.

- LessonSlot
  - Deterministic id computed from slot_number (as string) in __init__.
  - A CheckConstraint ensures end_time > start_time.
  - DDL event listener adds `CREATE EXTENSION IF NOT EXISTS btree_gist` before create and
    adds an exclusion constraint after table creation using tsrange on start_time::timestamp
    and end_time::timestamp to detect overlaps. This is an ORM workaround because
    SQLAlchemy does not have a direct high-level API for PostgreSQL exclusion constraints
    on arbitrary range expressions.
  - Note: The exclusion constraint uses time cast to timestamp which is a pragmatic
    approximation and may need refinement in Pass 2.

- Room
  - Deterministic id computed from room number in __init__.
  - room_type uses the RoomType enum mapped to a native PostgreSQL enum.

- Teacher
  - Deterministic id computed from first_name, last_name, and employment_date ISO string in __init__.
  - Unique constraint on (first_name, last_name, employment_date).

- Subject
  - Deterministic id computed from subject code in __init__.
  - required_room_type uses RoomType enum.

- GradeLevel
  - Deterministic id computed from name in __init__.
  - name is unique.

- Class
  - Random uuid4 primary key with server_default gen_random_uuid().
  - grade_level_id foreign key enforces relation to grade_levels.id.
  - Relationship to GradeLevel uses lazy="selectin" to optimize batch loads.

- GradeSubjectRequirement, TeacherSubject, TeacherAvailability (bridges)
  - Implemented as tables with composite primary keys and appropriate FKs.
  - Relationships use eager loading for small joins (lazy="joined") where the bridge entry
    is expected to be fetched alongside the related object.

- Schedule and ScheduleEntry
  - Schedule has is_active SmallInteger; `active` property returns boolean.
  - ScheduleEntry has partial unique indexes implemented via Index(..., postgresql_where=...)
    in __table_args__ to enforce uniqueness only when the referenced columns are not null.
  - Index conditions were expressed using Column("name") != None expressions to avoid
    referring to mapped attributes in a context where the table object is required.

- ScheduleEntryDraft
  - FK is enforced only for slot_id as requested. Other IDs are stored as UUID columns
    without foreign key constraints. `cache` property converts is_cache to bool.

- ImportStaging
  - raw_data uses SQLAlchemy JSON type. Status defaults to "pending" at the Python level.

- Loading strategy summary
  - Many-to-one relationships use lazy="joined" for fewer round trips when a single parent is
    expected to be consulted with the child.
  - Collection and parent-to-children relationships use lazy="selectin" to allow efficient
    batch loading in algorithmic processing.

- ORM workarounds
  - The exclusion constraint on LessonSlot uses raw DDL attached to the table via an
    event listener. The constraint casts time values to timestamp for range expressions.
  - The server-side gen_random_uuid() is referenced for uuid4 columns; ensure the database
    provides that function (pgcrypto or uuid-ossp may be required) or rely on Python-side defaults.

## Open Items for Pass 2
- Validate and refine the exclusion constraint on LessonSlot to correctly express time
  ranges within a day; consider using a dedicated range type or a normalized datetime
  with date anchor.
- Consider migrating raw_data to JSONB if queries will rely on indexing or containment.
- Confirm presence of `gen_random_uuid()` in target PostgreSQL; create pgcrypto extension
  as part of init_db if desired.
- Add factory constructors for deterministic-key models if callers will rarely provide ids.
- Add database migrations (alembic) to manage enum types and the exclusion constraint reliably.
