# Part 3 — SQL Storage and API Service

## Purpose

Part 3 turns the curated Part 2 MYH applications dataset into a small internal data service.

The project shows the path from a trusted curated dataset to PostgreSQL storage, a FastAPI API, and a backend structure that can support the remaining portfolio extensions: scheduled MYH source checking, protected operations, React visualization, and a small explainable ML layer. The implementation stays practical and explainable while using normal professional structure where it solves real project problems.

## Source of truth

The curated CSV from Part 2 is the loading source for the Part 3 database:

```text
myh_curated_applications_2020_2025.csv
```

Current dataset facts:

```text
Rows: 7,641
Years: 2020-2025
Main record identifier: diarienummer
Main grain: one application record per diarienummer
```

The raw Excel files are not loaded directly by the current Part 3 API. They belong to the Part 2 transformation journey. Sub-project 3.11 is planned to add a controlled scheduled source-check workflow for newly published MYH files.

## Implementation principles

- Use PostgreSQL as the database.
- Use FastAPI for the backend API.
- Use psycopg 3 for PostgreSQL access.
- Use raw SQL for database queries.
- Do not use an ORM.
- Keep endpoint behavior backward compatible unless a real bug is found.
- Add structure only when it improves maintainability, validation, or later roadmap work.
- Keep internal handoff/control files outside Git tracking.

## Current backend shape after Sub-project 3.10

Sub-project 3.10 reorganized the accepted 3.8 backend into routers and services, added database readiness checks, logging, centralized database-error handling, and focused pytest coverage.

```text
part_3/
  README.md
  pyproject.toml
  backend/
    README.md
    requirements.txt
    app/
      __init__.py
      database.py
      dependencies.py
      exception_handlers.py
      logging_config.py
      main.py
      queries.py                 # compatibility exports for older imports
      schemas.py
      routers/
        __init__.py
        applications.py
        export.py
        health.py
        operations.py
        providers.py
        stats.py
      services/
        __init__.py
        applications.py
        common.py
        export.py
        health.py
        providers.py
        stats.py
    scripts/
      demo_api.py
      load_curated_data.py
      smoke_test_api.py
      validate_database.py
    sql/
      schema.sql
      indexes.sql
    tests/
      test_filter_helpers.py
      test_health_service.py
      test_routes.py
      test_schemas_and_export.py
```

`main.py` is now app assembly only. Route code lives in `backend/app/routers/`. Database-backed query/business logic lives in `backend/app/services/`. Response models remain in `schemas.py` because splitting small schemas further was not necessary for this step.

## Database shape

The database is normalized enough to support useful API queries without becoming difficult to explain.

Core tables:

```text
applications
providers
education_areas
locations
decisions
principal_types
study_forms
```

The `applications` table remains the central table. Repeated high-value fields such as provider, education area, location, decision, principal type, and study form are represented through lookup tables.

Traceability fields from the curated dataset are preserved:

```text
source_year
source_file
source_sheet
source_row
diarienummer
```

## API story

The API reads from PostgreSQL and provides:

- service and database readiness checks,
- record access,
- filtered and paginated browsing,
- grouped statistics,
- provider browsing,
- filtered CSV export,
- trend statistics over `source_year`,
- one controlled operational refresh endpoint.

Implemented endpoints:

```text
GET  /
GET  /health
GET  /health/db
GET  /applications
GET  /applications/{diarienummer}
GET  /stats/by-year
GET  /stats/by-region
GET  /stats/by-education-area
GET  /stats/by-decision
GET  /stats/trends/by-decision
GET  /stats/trends/by-region
GET  /stats/trends/by-education-area
GET  /providers
GET  /providers/{provider_id}/applications
GET  /export/applications
POST /refresh
```

### `/health` versus `/health/db`

`GET /health` is intentionally lightweight. It only confirms that the FastAPI process can respond.

`GET /health/db` checks database readiness for real API use. It verifies that the database connection works, required tables exist, the `applications` table has rows, and key lookup tables have rows. This endpoint is useful for local validation now and for the planned React dashboard later.

## Filters and exports

`GET /applications` supports useful filters and pagination:

```text
source_year
decision
region or lan
municipality or kommun
provider
education_area
study_form
limit
offset
```

`GET /providers` supports `q`, `limit`, and `offset`. Provider detail paths use numeric `provider_id` values because provider names can contain spaces, punctuation, Swedish characters, and organization suffixes.

`GET /export/applications` supports filtered CSV downloads with assignment-style examples:

```text
GET /export/applications?year=2024&decision=approved
GET /export/applications?provider=KYH
GET /export/applications?provider_id=1
```

Trend endpoints support `year_from` and `year_to`. Decision trends can be filtered by `decision`, region trends by `region` or `lan`, and education-area trends by `education_area`. Region and education-area trends also support `limit` to return top groups for presentation or charting.

`POST /refresh` reloads PostgreSQL from the existing curated CSV. It validates required columns and expected dataset assumptions, recreates the current schema, reloads lookup tables and applications, and returns a short JSON summary. Sub-project 3.11 is planned to improve the source-check/refresh story with a scheduler-friendly MYH source check.

## Local validation flow

From `part_3`, install dependencies once in your normal Python environment:

```bash
pip install -r backend/requirements.txt
```

Set `DATABASE_URL`.

Windows PowerShell:

```powershell
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/myh_applications"
```

macOS/Linux:

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/myh_applications"
```

Compile-check the backend:

```bash
python -m py_compile backend/app/*.py backend/app/routers/*.py backend/app/services/*.py backend/scripts/*.py
```

Run the focused tests:

```bash
python -m pytest
```

Load or refresh the database from the curated CSV:

```bash
python backend/scripts/load_curated_data.py --csv-path ../path/to/myh_curated_applications_2020_2025.csv
```

Validate that PostgreSQL matches the curated CSV:

```bash
python backend/scripts/validate_database.py --csv-path ../path/to/myh_curated_applications_2020_2025.csv
```

Start the API:

```bash
uvicorn backend.app.main:app --reload
```

Manual browser/API checks:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/health
http://127.0.0.1:8000/health/db
http://127.0.0.1:8000/docs
```

In another terminal, run the final smoke test:

```bash
python backend/scripts/smoke_test_api.py
```

For a presentation-friendly endpoint sequence, run:

```bash
python backend/scripts/demo_api.py
python backend/scripts/demo_api.py --print-only
```

To include the operational refresh call in the demo sequence:

```bash
python backend/scripts/demo_api.py --include-refresh
```

## Expanded roadmap after 3.10

The assignment remains the baseline for required deliverables, but the assessor has allowed stronger additions when they remain explainable at vocational/YH-student level and improve the final project/demo value.

Current roadmap:

```text
3.10 Backend Structure and Robustness Foundation — completed
3.11 Scheduled MYH Source Check and Refresh Upgrade — next
3.12 Protected Admin Operations and Safe Write Use Case
3.13 React + TypeScript Visualization and Trend Dashboard
3.14 Small Explainable ML Extension
3.15 Final Integration, Presentation Update, and Submission Cleanup
```

Guiding rule:

```text
Vocational level means explainable and proportionate, not toy-like or artificially weak. Use normal professional structure when it improves correctness, maintainability, robustness, or presentation value.
```

No React frontend, ML module, scheduled MYH source checking, or protected admin write operation is implemented in 3.10.

## Git policy

Commit by coherent logical change.

Do not commit:

```text
virtual environments
node_modules
.env files
database dumps
local runtime files
internal handoff/control files
```
