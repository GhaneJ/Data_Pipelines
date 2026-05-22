# Part 3 Backend — Database Layer

This folder contains the PostgreSQL database work for Sub-project 3.2.

The current scope is only the database foundation:

```text
backend/
  sql/
    schema.sql
    indexes.sql
  scripts/
    load_curated_data.py
    validate_database.py
  requirements.txt
```

No FastAPI application is implemented in this sub-project.

## Database choice

The project uses PostgreSQL with raw SQL and psycopg 3. No ORM is used.

The database is normalized, but intentionally simple. The central table is `applications`, with lookup tables for repeated values that are useful for future filtering and explanation:

```text
decisions
providers
education_areas
locations
principal_types
study_forms
```

`diarienummer` is used as the natural application identifier because the curated CSV has been validated as unique.

## Install dependencies

From `part_3`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

## Configure PostgreSQL connection

Set `DATABASE_URL` before running the scripts.

macOS/Linux:

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/myh_applications"
```

Windows PowerShell:

```powershell
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/myh_applications"
```

Adjust user, password, host, port, and database name to match your local PostgreSQL setup.

## Load the curated CSV

From `part_3`:

```bash
python backend/scripts/load_curated_data.py --csv-path ../path/to/myh_curated_applications_2020_2025.csv
```

By default, the loader runs `schema.sql` and `indexes.sql` first. That recreates the tables, then loads the lookup rows and application rows.

## Validate the database

```bash
python backend/scripts/validate_database.py --csv-path ../path/to/myh_curated_applications_2020_2025.csv
```

The validator checks:

- row count after load,
- unique `diarienummer`,
- year range 2020-2025,
- expected normalized decision values,
- no unexpected loss of records,
- foreign-key consistency for lookup tables.

## Current boundary

This sub-project stops at database loading and validation. The FastAPI read API belongs in Sub-project 3.3.
