# Part 3 — SQL Storage and API Service

## Purpose

Part 3 turns the curated Part 2 MYH applications dataset into a small internal data service.

The project shows the path from a trusted curated dataset to PostgreSQL storage, a FastAPI API, protected admin metadata operations, and a backend structure that can support the remaining portfolio extensions: React visualization and a small explainable ML layer. The implementation stays practical and explainable while using normal professional structure where it solves real project problems.

## Source of truth

The curated CSV from Part 2 is still the loading source for the Part 3 database:

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

Sub-project 3.11 added a controlled MYH source-check foundation. It can inspect the configured official MYH result page, record a local source-status manifest, and help decide whether the local curated CSV may be stale. It does **not** automatically download new Excel files or overwrite the curated dataset.

Sub-project 3.12 adds a protected admin write use case: local application notes stored in a separate metadata table. Admin notes do **not** modify the curated MYH source data and require a configured `PART3_ADMIN_TOKEN` sent as `X-Admin-Token`.

## Implementation principles

- Use PostgreSQL as the database.
- Use FastAPI for the backend API.
- Use psycopg 3 for PostgreSQL access.
- Use raw SQL for database queries.
- Do not use an ORM.
- Keep endpoint behavior backward compatible unless a real bug is found.
- Add structure only when it improves maintainability, validation, operations, or later roadmap work.
- Keep generated runtime files and internal handoff/control files outside Git tracking.

## Current backend shape after Sub-project 3.12

Sub-project 3.10 reorganized the backend into routers and services, added database readiness checks, logging, centralized database-error handling, and focused pytest coverage.

Sub-project 3.11 added a modest scheduled-source-check foundation and refresh metadata upgrade. Sub-project 3.12 added protected admin notes as a safe write-side use case.

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
      security.py                # simple PART3_ADMIN_TOKEN / X-Admin-Token dependency
      routers/
        __init__.py
        admin.py                 # protected application-note endpoints
        applications.py
        export.py
        health.py
        operations.py
        providers.py
        stats.py
      services/
        __init__.py
        admin_notes.py            # local admin-note storage service
        applications.py
        common.py
        export.py
        health.py
        providers.py
        source_check.py           # MYH source-page check and manifest helpers
        stats.py
    runtime/
      README.md                   # generated source_status.json belongs here locally
    scripts/
      check_source_status.py      # manual/scheduler-ready source-check script
      demo_api.py
      load_curated_data.py
      smoke_test_api.py
      validate_database.py
    sql/
      schema.sql
      indexes.sql
    tests/
      test_admin_auth.py
      test_admin_notes_service.py
      test_admin_routes.py
      test_check_source_status_script.py
      test_filter_helpers.py
      test_health_service.py
      test_operations_routes.py
      test_routes.py
      test_schemas_and_export.py
      test_source_check_service.py
```

`main.py` remains app assembly only. Route code lives in `backend/app/routers/`. Database-backed query/business logic lives in `backend/app/services/`. Response models remain in `schemas.py` because splitting small schemas further is still unnecessary.

## Database shape

The database is normalized enough to support useful API queries without becoming difficult to explain.

Core curated-data tables:

```text
applications
providers
education_areas
locations
decisions
principal_types
study_forms
```

Local admin metadata table:

```text
application_notes
```

The `applications` table remains the central curated-data table. Repeated high-value fields such as provider, education area, location, decision, principal type, and study form are represented through lookup tables. The `application_notes` table is separate local metadata for protected admin use and does not overwrite source data.

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
- MYH source-check status and manual source-check operation,
- protected admin notes attached to applications,
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
GET  /operations/source-status
POST /operations/check-source
GET  /admin/applications/{diarienummer}/notes
POST /admin/applications/{diarienummer}/notes
PUT  /admin/notes/{note_id}
PATCH /admin/notes/{note_id}
DELETE /admin/notes/{note_id}
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

## MYH source-check foundation

Sub-project 3.11 introduces a small source-check layer:

```text
backend/app/services/source_check.py
backend/scripts/check_source_status.py
backend/runtime/README.md
```

The source check can:

- call the configured MYH result source page,
- discover visible Excel links when simple link extraction is enough,
- include configured/allowlisted file names or URLs through environment variables or script arguments,
- compare the latest visible source year with the local curated CSV `source_year`,
- write a local JSON manifest at `backend/runtime/source_status.json`,
- report whether the local curated data appears up to date, possibly stale, or needs manual review.

The source check does **not**:

- run as a background service,
- create an operating-system scheduled task,
- download and replace raw Excel files,
- rebuild the Part 2 notebook output,
- overwrite the curated CSV,
- refresh PostgreSQL automatically.

Useful environment variables:

```text
MYH_SOURCE_URL                         # override the official source page URL
MYH_SOURCE_FILES                       # comma-separated known source file names or URLs
MYH_SOURCE_STATUS_PATH                 # override backend/runtime/source_status.json
MYH_CURATED_CSV_PATH                   # explicit curated CSV path for source_year comparison
MYH_SOURCE_CHECK_TIMEOUT_SECONDS       # HTTP timeout for the source check
```

Manual script:

```bash
python backend/scripts/check_source_status.py
python backend/scripts/check_source_status.py --no-write-manifest
python backend/scripts/check_source_status.py --configured-file resultat-2025.xlsx
```

API endpoints:

```bash
curl "http://127.0.0.1:8000/operations/source-status"
curl -X POST "http://127.0.0.1:8000/operations/check-source"
```

`GET /operations/source-status` reads the latest local manifest and does not call the internet. If no check has been recorded, it returns `status: "not_checked"`.

`POST /operations/check-source` performs one manual source check and writes/updates the local manifest. It does not modify application data.

Generated source manifests are local runtime files and should not be committed:

```text
backend/runtime/source_status.json
```

## Protected admin application notes

Sub-project 3.12 adds one small write-side feature under `/admin`: local notes linked to application `diarienummer` values. Public read endpoints remain public. Admin note text is only available through protected `/admin` endpoints.

Configuration:

```text
PART3_ADMIN_TOKEN=<your-local-token>
```

Protected requests must include:

```text
X-Admin-Token: <your-local-token>
```

Admin note endpoints:

```text
GET    /admin/applications/{diarienummer}/notes
POST   /admin/applications/{diarienummer}/notes
PUT    /admin/notes/{note_id}
PATCH  /admin/notes/{note_id}
DELETE /admin/notes/{note_id}
```

`PUT` replaces the note text with the submitted full value. `PATCH` supports a partial update request; in the current simple note model, `note_text` is the only editable field, so an empty PATCH body returns a clear `400`.

Example calls, with URL-encoded `diarienummer` when it contains spaces or slashes:

```bash
curl -H "X-Admin-Token: <your-local-token>" \
  "http://127.0.0.1:8000/admin/applications/MYH%202024%2F1/notes"

curl -H "X-Admin-Token: <your-local-token>" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{"note_text":"Check this application before the demo."}' \
  "http://127.0.0.1:8000/admin/applications/MYH%202024%2F1/notes"

curl -H "X-Admin-Token: <your-local-token>" \
  -H "Content-Type: application/json" \
  -X PUT \
  -d '{"note_text":"Replace the local note text."}' \
  "http://127.0.0.1:8000/admin/notes/1"

curl -H "X-Admin-Token: <your-local-token>" \
  -H "Content-Type: application/json" \
  -X PATCH \
  -d '{"note_text":"Partially update the local note text."}' \
  "http://127.0.0.1:8000/admin/notes/1"
```

Safety boundaries:

- the curated `applications` table is not overwritten by admin notes,
- notes are stored in the separate `application_notes` table,
- the service validates that an application exists before creating or listing notes,
- missing or wrong request tokens return clear auth errors,
- a missing server token returns a clear configuration error,
- there are no users, login pages, sessions, OAuth flows, or passwords.

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

## Operational refresh

`POST /refresh` still reloads PostgreSQL from the existing curated CSV. It validates required columns and expected dataset assumptions, recreates the current schema, reloads lookup tables and applications, and returns a JSON summary.

3.11 adds source-check metadata to the refresh response when a source-status manifest is available. The endpoint remains safe: it does not download new MYH files or overwrite the curated CSV.

Example:

```bash
curl -X POST "http://127.0.0.1:8000/refresh"
```

Optional guardrail:

```bash
curl -X POST "http://127.0.0.1:8000/refresh?require_recent_source_check=true"
```

When `require_recent_source_check=true`, refresh is rejected unless a recent non-error source-check manifest exists. The default maximum age is 24 hours and can be adjusted:

```bash
curl -X POST "http://127.0.0.1:8000/refresh?require_recent_source_check=true&max_source_check_age_hours=48"
```

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
python -m compileall backend/app backend/scripts
```

Run the focused tests:

```bash
python -m pytest
```

Print the final demo sequence without calling the API:

```bash
python backend/scripts/demo_api.py --print-only
```

Run the source-check script manually:

```bash
python backend/scripts/check_source_status.py
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
http://127.0.0.1:8000/operations/source-status
http://127.0.0.1:8000/admin/applications/{diarienummer}/notes
http://127.0.0.1:8000/docs
```

In another terminal, run the smoke test:

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

## Expanded roadmap after 3.12

The assignment remains the baseline for required deliverables, but the assessor has allowed stronger additions when they remain explainable at vocational/YH-student level and improve the final project/demo value.

Current roadmap:

```text
3.10 Backend Structure and Robustness Foundation — completed
3.11 Scheduled MYH Source Check and Refresh Upgrade — completed
3.12 Protected Admin Operations and Safe Write Use Case — completed
3.13 React + TypeScript Visualization and Trend Dashboard — next
3.14 Small Explainable ML Extension
3.15 Final Integration, Presentation Update, and Submission Cleanup
```

Guiding rule:

```text
Vocational level means explainable and proportionate, not toy-like or artificially weak. Use normal professional structure when it improves correctness, maintainability, robustness, operations, or presentation value.
```

No React frontend or ML module is implemented in 3.12. Protected admin notes are implemented with create, list, replace, partial update, and delete operations, but full user accounts, login flows, and complex authorization remain intentionally excluded.

## Git policy

Commit by coherent logical change.

Do not commit:

```text
virtual environments
node_modules
.env files
database dumps
local runtime/generated files such as backend/runtime/source_status.json
internal handoff/control files
```
