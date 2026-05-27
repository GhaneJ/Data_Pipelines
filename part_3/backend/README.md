# Part 3 Backend — PostgreSQL and FastAPI

This folder contains the Part 3 backend for storing and exposing the curated MYH applications dataset.

Sub-projects 3.2-3.8 built the working backend gradually: PostgreSQL storage, core read API, richer statistics, provider browsing, filtered CSV export, trend statistics, operational refresh, and final validation/demo readiness.

Sub-project 3.10 reorganized that backend into a clearer structure and added database readiness checks, simple logging, centralized database-error handling, and focused pytest coverage.

Sub-project 3.11 added a scheduler-ready MYH source-check foundation, local source-status manifest, source-check operation endpoints, refresh metadata, a manual source-check script, and focused tests that do not depend on live internet access. Sub-project 3.12 adds protected admin application notes as a small safe write-side use case. Sub-project 3.12.1 adds safe database seeder/startup initialization with SQL files as the single schema source of truth. Sub-project 3.13 adds minimal local-development CORS support so the React/Vite dashboard can call the public API from the browser.

## Technology choices

The backend uses:

- PostgreSQL for SQL storage,
- psycopg 3 for PostgreSQL access,
- FastAPI for the API,
- raw SQL for queries,
- Pydantic/FastAPI response models where they make JSON responses easier to understand,
- pytest for focused backend tests,
- narrow local-development CORS for the React dashboard.

No ORM is used.

## Backend structure

```text
backend/
  app/
    main.py                  FastAPI app assembly and router registration
    database.py              DATABASE_URL handling and psycopg connection helper
    dependencies.py          request-scoped database dependency
    exception_handlers.py    central handlers for expected database failures
    logging_config.py        simple local logging setup
    schemas.py               response models
    queries.py               compatibility exports for older imports
    routers/
      health.py              /, /health, /health/db
      applications.py        /applications routes
      stats.py               statistics and trend routes
      providers.py           provider browsing routes
      export.py              CSV export route
      operations.py          refresh and source-check operation routes
      admin.py               protected admin-note routes
    services/
      common.py              shared filters and SQL helpers
      applications.py        application browsing and lookup queries
      stats.py               statistics and trend queries
      providers.py           provider browsing queries
      export.py              CSV export query and serializer
      health.py              database readiness checks
      database_seeder.py     safe startup schema/index bootstrap
      admin_notes.py         protected local admin-note storage
      source_check.py        MYH source-page check and manifest helpers
  runtime/
    README.md                explains local generated runtime files
  sql/
    reset_schema.sql         explicit full-reload reset, never used by startup
    schema.sql               safe CREATE TABLE IF NOT EXISTS schema source
    indexes.sql              safe CREATE INDEX IF NOT EXISTS indexes
  scripts/
    load_curated_data.py
    validate_database.py
    smoke_test_api.py
    demo_api.py
    check_source_status.py
  tests/
    test_admin_auth.py
    test_admin_notes_service.py
    test_admin_routes.py
    test_check_source_status_script.py
    test_cors.py
    test_database_seeder.py
    test_filter_helpers.py
    test_health_service.py
    test_load_curated_data.py
    test_operations_routes.py
    test_routes.py
    test_schemas_and_export.py
    test_source_check_service.py
```

`main.py` should stay small. New endpoint work should normally go into a router, with database/query or operation logic placed in a service module. The only 3.13 backend support change is narrow CORS middleware for local React dashboard development. The next implementation layer is the small explainable ML extension.

## Install dependencies

From `part_3`, use the Python environment you normally run this project with:

```bash
pip install -r backend/requirements.txt
```

## Configure PostgreSQL connection

Set `DATABASE_URL` before running database scripts or starting the FastAPI app. The PostgreSQL database itself must already exist; the backend creates/checks project-managed tables and indexes inside that existing database.

Windows PowerShell:

```powershell
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/myh_applications"
```

macOS/Linux:

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/myh_applications"
```

Adjust user, password, host, port, and database name to match your local PostgreSQL setup.

## Startup database seeder

FastAPI startup runs `backend.app.services.database_seeder.ensure_database_ready()`.

The seeder:

- reads `DATABASE_URL`,
- connects to the existing PostgreSQL database,
- runs safe `schema.sql` and `indexes.sql`,
- seeds fixed decision lookup rows with `ON CONFLICT`,
- includes `application_notes` as a normal project-managed table,
- does not run `reset_schema.sql`,
- does not reload the curated CSV,
- does not drop, truncate, delete, or overwrite existing rows.

SQL ownership is deliberately simple:

```text
backend/sql/schema.sql        safe table definitions used by startup and loader
backend/sql/indexes.sql       safe index definitions used by startup and loader
backend/sql/reset_schema.sql  explicit curated-data reset used only by loader/refresh
```

## Load the curated CSV

From `part_3`:

```bash
python backend/scripts/load_curated_data.py --csv-path ../path/to/myh_curated_applications_2020_2025.csv
```

By default, the loader runs `reset_schema.sql`, then the safe `schema.sql`, then `indexes.sql`. This keeps destructive full reload behavior explicit and separate from API startup. The loader reloads lookup rows and application rows from the curated CSV. The API refresh endpoint uses the same loading helper. `application_notes` is not reset by the curated-data reload.

## Validate the database

```bash
python backend/scripts/validate_database.py --csv-path ../path/to/myh_curated_applications_2020_2025.csv
```

The validator checks row count, unique `diarienummer`, year coverage, normalized decisions, record preservation, and lookup-table foreign-key consistency.

## MYH source checking

The 3.11 source-check layer is intentionally modest and explainable.

It can:

- reach the configured MYH source page,
- discover simple visible Excel links from the source-page HTML,
- include configured file names or URLs when automatic discovery is not enough,
- compare the latest visible source year with the local curated CSV `source_year`,
- write a local manifest to `backend/runtime/source_status.json`,
- provide status information for a later Windows Task Scheduler or cron workflow.

It does not:

- download and overwrite MYH Excel files,
- rewrite the Part 2 curated CSV,
- run as a background scheduler,
- refresh PostgreSQL automatically,
- use the protected admin-note endpoints added in 3.12.

Environment variables:

```text
MYH_SOURCE_URL
MYH_SOURCE_FILES
MYH_SOURCE_STATUS_PATH
MYH_CURATED_CSV_PATH
MYH_SOURCE_CHECK_TIMEOUT_SECONDS
```

Manual script:

```bash
python backend/scripts/check_source_status.py
python backend/scripts/check_source_status.py --no-write-manifest
python backend/scripts/check_source_status.py --configured-file resultat-2025.xlsx
```

The default manifest path is:

```text
backend/runtime/source_status.json
```

That JSON file is generated local machine state and should not be committed. The folder README is tracked so the intended runtime location is clear.

## Run focused tests

The pytest layer is intentionally small. It does not require a live PostgreSQL database, and the source-check tests use mocked HTTP responses instead of live internet.

From `part_3`:

```bash
python -m pytest
```

Current test focus:

- lightweight health endpoints,
- route registration after the router refactor,
- filter/query helper guardrails,
- export year-alias guardrail,
- trend year-range guardrail,
- database-readiness service behavior using monkeypatching,
- source-check parsing, manifest, and mocked response behavior,
- source-check operation routes,
- source-check script formatting,
- basic schema and CSV serialization.

## Run the API locally

From `part_3`:

```bash
uvicorn backend.app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/health
http://127.0.0.1:8000/health/db
http://127.0.0.1:8000/operations/source-status
http://127.0.0.1:8000/docs
```

`/docs` opens the automatic Swagger/OpenAPI documentation generated by FastAPI.


## Local dashboard CORS

Sub-project 3.13 adds narrow CORS middleware for local React/Vite development only.

Allowed origins:

```text
http://localhost:5173
http://127.0.0.1:5173
```

Allowed methods are limited to `GET` and `OPTIONS`, which is enough for the public dashboard endpoints. This does not expose admin tokens, does not weaken `PART3_ADMIN_TOKEN`, and does not change protected `/admin` behavior.

The React dashboard uses public endpoints only:

```text
GET /health
GET /health/db
GET /applications
GET /applications/{diarienummer}
GET /stats/by-year
GET /stats/by-region
GET /stats/by-education-area
GET /stats/by-decision
GET /stats/trends/by-decision
GET /stats/trends/by-education-area
```

## Health and source-status endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Lightweight process check. It confirms that FastAPI can respond. |
| `GET /health/db` | Database readiness check. It confirms connection, required tables, application rows, and lookup rows. |
| `GET /operations/source-status` | Reads the latest local source-check manifest without calling the internet. |
| `POST /operations/check-source` | Performs one source check and writes the local source-status manifest. |

Use `/health` for quick “is the API process alive?” checks. Use `/health/db` before demonstrations or frontend work that depends on actual loaded data. Use `/operations/source-status` and `/operations/check-source` to explain how the backend is ready for a manual or scheduled source-check workflow.

## Endpoint overview

### Service and operational endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /` | Small service landing response for browser checks. |
| `GET /health` | Confirms that the API process is running. |
| `GET /health/db` | Confirms database readiness for real API use. |
| `GET /operations/source-status` | Shows the latest MYH source-check manifest. |
| `POST /operations/check-source` | Checks the configured MYH source page and updates the manifest. |
| `POST /refresh` | Reloads PostgreSQL from the existing curated CSV. |
| `GET /admin/applications/{diarienummer}/notes` | Protected local admin-note listing. |
| `POST /admin/applications/{diarienummer}/notes` | Protected local admin-note creation. |
| `PUT /admin/notes/{note_id}` | Protected local admin-note replacement. |
| `PATCH /admin/notes/{note_id}` | Protected local admin-note partial update. |
| `DELETE /admin/notes/{note_id}` | Protected local admin-note deletion. |

### Record access and browsing

| Endpoint | Purpose |
| --- | --- |
| `GET /applications` | Paginated application browsing with useful filters. |
| `GET /applications/{diarienummer}` | Fetches one application by natural identifier. |
| `GET /providers` | Lists providers with counts and optional provider-name search. |
| `GET /providers/{provider_id}/applications` | Lists applications for one provider ID. |

### Statistics and trends

| Endpoint | Purpose |
| --- | --- |
| `GET /stats/by-year` | Aggregates applications by source year. |
| `GET /stats/by-region` | Aggregates applications by län/region. |
| `GET /stats/by-education-area` | Aggregates applications by education area. |
| `GET /stats/by-decision` | Aggregates applications by normalized decision. |
| `GET /stats/trends/by-decision` | Yearly counts by normalized decision. |
| `GET /stats/trends/by-region` | Yearly counts by län/region. |
| `GET /stats/trends/by-education-area` | Yearly counts by education area. |

### Export

| Endpoint | Purpose |
| --- | --- |
| `GET /export/applications` | Returns a downloadable filtered CSV export. |

## Protected admin application notes

Sub-project 3.12 adds a small local write-side feature under `/admin`. It is deliberately not a login system. The server reads one configured token from `PART3_ADMIN_TOKEN`, and callers send the same value in the `X-Admin-Token` header.

PowerShell example:

```powershell
$env:PART3_ADMIN_TOKEN="dev-admin-token"
```

Bash/macOS/Linux example:

```bash
export PART3_ADMIN_TOKEN="dev-admin-token"
```

Example protected calls:

```bash
curl -H "X-Admin-Token: dev-admin-token" \
  "http://127.0.0.1:8000/admin/applications/MYH%202024%2F1/notes"

curl -H "X-Admin-Token: dev-admin-token" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{"note_text":"Check this application before the demo."}' \
  "http://127.0.0.1:8000/admin/applications/MYH%202024%2F1/notes"

curl -H "X-Admin-Token: dev-admin-token" \
  -H "Content-Type: application/json" \
  -X PUT \
  -d '{"note_text":"Replace the local note text."}' \
  "http://127.0.0.1:8000/admin/notes/1"

curl -H "X-Admin-Token: dev-admin-token" \
  -H "Content-Type: application/json" \
  -X PATCH \
  -d '{"note_text":"Partially update the local note text."}' \
  "http://127.0.0.1:8000/admin/notes/1"

curl -H "X-Admin-Token: dev-admin-token" \
  -X DELETE "http://127.0.0.1:8000/admin/notes/1"
```

The note table is `application_notes`. It stores local admin metadata only. It does not change `applications` or any MYH source file. The service validates that a `diarienummer` exists before writing or listing notes. `PUT` replaces the note text. `PATCH` supports partial update semantics; because the current model has one editable field, it updates `note_text` when provided and rejects an empty body with `400`.

Auth behavior:

- missing `PART3_ADMIN_TOKEN` on the server: protected admin endpoints return a clear configuration error,
- missing `X-Admin-Token`: unauthorized,
- wrong `X-Admin-Token`: forbidden,
- correct token: the endpoint proceeds to the note operation.

## Common example requests

### Source status and source check

```bash
curl "http://127.0.0.1:8000/operations/source-status"
curl -X POST "http://127.0.0.1:8000/operations/check-source"
```

`GET /operations/source-status` is safe to call frequently because it only reads the local manifest. `POST /operations/check-source` performs a live page check and updates the manifest, but does not modify application data.

### List applications

```bash
curl "http://127.0.0.1:8000/applications?limit=5"
curl "http://127.0.0.1:8000/applications?source_year=2024&decision=approved&region=Skåne&limit=10"
```

Supported query parameters:

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

`limit` defaults to 50 and is capped at 500. `offset` defaults to 0.

### Get one application

`diarienummer` values can contain spaces and slashes, so encode them in manual URLs:

```bash
curl "http://127.0.0.1:8000/applications/MYH%202020%2F4419"
```

### Statistics

```bash
curl "http://127.0.0.1:8000/stats/by-year"
curl "http://127.0.0.1:8000/stats/by-region"
curl "http://127.0.0.1:8000/stats/by-education-area"
curl "http://127.0.0.1:8000/stats/by-decision"
```

Statistics responses include application counts and useful grouped measures such as approval rates or application shares.

### Trend statistics

Trend endpoints show how application counts develop over `source_year`.

```bash
curl "http://127.0.0.1:8000/stats/trends/by-decision?year_from=2022&year_to=2025"
curl "http://127.0.0.1:8000/stats/trends/by-decision?decision=approved"
curl "http://127.0.0.1:8000/stats/trends/by-region?year_from=2023&year_to=2025&limit=5"
curl "http://127.0.0.1:8000/stats/trends/by-region?region=Stockholm"
curl "http://127.0.0.1:8000/stats/trends/by-education-area?year_from=2023&year_to=2025&limit=5"
curl "http://127.0.0.1:8000/stats/trends/by-education-area?education_area=Data%2FIT"
```

Supported trend query parameters:

```text
year_from
year_to
decision              # by-decision only
region or lan         # by-region only
education_area        # by-education-area only
limit                 # by-region and by-education-area only
```

If both `year_from` and `year_to` are provided, `year_from` must be less than or equal to `year_to`.

### Provider browsing

```bash
curl "http://127.0.0.1:8000/providers?limit=10"
curl "http://127.0.0.1:8000/providers?q=KYH&limit=5"
curl "http://127.0.0.1:8000/providers/1/applications?limit=10"
```

Use `GET /providers` first to find the `provider_id`. Provider paths use numeric IDs because provider names may contain spaces, punctuation, Swedish characters, and organization suffixes.

### Export filtered applications as CSV

```bash
curl -OJ "http://127.0.0.1:8000/export/applications?year=2024&decision=approved"
curl -OJ "http://127.0.0.1:8000/export/applications?provider=KYH"
curl -OJ "http://127.0.0.1:8000/export/applications?provider_id=1"
curl -OJ "http://127.0.0.1:8000/export/applications?year=2025&region=Stockholm&limit=100"
```

The endpoint returns a downloadable file named:

```text
myh_applications_export.csv
```

Supported export query parameters:

```text
year
source_year
decision
region or lan
municipality or kommun
education_area
provider
provider_id
study_form
limit
```

`year` is the preferred user-facing filter and maps to the database field `source_year`. `source_year` is also accepted as an alias. If both are used, they must have the same value.

### Operational refresh

```bash
curl -X POST "http://127.0.0.1:8000/refresh"
```

Example response shape:

```json
{
  "status": "success",
  "rows_loaded": 7641,
  "source_file": "part_2/data/processed/myh_curated_applications_2020_2025.csv",
  "refreshed_at": "2026-05-27T14:30:00+00:00",
  "refresh_mode": "curated_csv",
  "source_check_status": "up_to_date",
  "source_check_checked_at": "2026-05-27T13:45:00+00:00",
  "source_check_message": "Local curated data is aligned with the latest visible source year (2025).",
  "known_latest_source_snapshot": 2025,
  "local_latest_source_year": 2025,
  "source_up_to_date": true
}
```

Current refresh behavior:

- reloads from the existing curated CSV,
- validates required columns and expected dataset assumptions,
- runs the explicit curated-data reset and then the safe PostgreSQL schema,
- reloads lookup tables and applications,
- includes source-check metadata when a manifest is available,
- does not download or replace source Excel files,
- preserves local `application_notes` rows.

Optional guardrail:

```bash
curl -X POST "http://127.0.0.1:8000/refresh?require_recent_source_check=true"
```

If this query parameter is set to `true`, the endpoint requires a recent non-error source-check manifest before it reloads PostgreSQL from the existing curated CSV. This prepares the project for a scheduled workflow without creating a production scheduler.

## Smoke test and demo helper

Start the API first:

```bash
uvicorn backend.app.main:app --reload
```

In another terminal, run:

```bash
python backend/scripts/smoke_test_api.py
python backend/scripts/demo_api.py
python backend/scripts/demo_api.py --print-only
```

The smoke test checks the root endpoint, `/health`, `/health/db`, `/operations/source-status`, refresh, core browsing/statistics/provider/export endpoints, and important guardrails. Admin-note endpoints are shown in the demo helper but are not required by the smoke test unless you choose to test them manually with `PART3_ADMIN_TOKEN`.

## 3.13 scope boundary

Implemented by the end of 3.13:

- MYH source-check service,
- local JSON manifest support,
- `GET /operations/source-status`,
- `POST /operations/check-source`,
- refresh response metadata and optional recent-source-check guardrail,
- manual `check_source_status.py` script,
- focused tests for source-check logic and operation routes,
- README/control-file updates,
- protected admin application notes under `/admin`,
- `application_notes` local metadata table,
- admin token dependency using `PART3_ADMIN_TOKEN` and `X-Admin-Token`,
- safe startup database seeder through `schema.sql` and `indexes.sql`,
- React + TypeScript dashboard in `part_3/frontend`,
- local-development CORS for the Vite dashboard.

Still not implemented after 3.13:

- ML extension,
- authentication or user accounts,
- automatic source-file download and curated CSV replacement,
- production scheduler or background worker,
- ORM conversion.
