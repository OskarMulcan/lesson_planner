Developer setup and first run instructions.

1. Install uv

Windows (PowerShell):

    python -m pip install --user pipx
    python -m pipx ensurepath
    pipx install uv

macOS (Homebrew):

    brew install python
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    pipx install uv

Linux (pipx):

    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    pipx install uv

2. Project initialization commands used

    uv init lesson_planner --package --python 3.14
    cd lesson_planner
    uv add sqlalchemy alembic pydantic pydantic-settings psycopg python-dotenv typer

3. Manual pyproject.toml edit

Add the following under the [project] table if it is not present:

[project.scripts]
lesson-planner = "lesson_planner.cli.main:app"

4. Create environment file

    cp .env.example .env

Required fields: DB_NAME, DB_USER, DB_PASSWORD
Optional fields: LOG_FILE_PATH (required only if LOG_TO_FILE=1), LOG_LEVEL, ENVIRONMENT

5. First-run sequence

    lesson-planner db init

Then import reference data in dependency order, for example:

    grade levels -> subjects -> rooms -> teachers -> classes -> schedules

6. Notes

The database initialization creates the btree_gist extension if available. If your
PostgreSQL instance requires additional extensions for uuid generation (for example
pgcrypto for gen_random_uuid), enable them before relying on server-side UUIDs.
