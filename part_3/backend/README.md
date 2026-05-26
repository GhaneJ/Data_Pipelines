# Part 3 Backend — PostgreSQL and FastAPI

This folder contains the Part 3 backend for storing and exposing the curated MYH applications dataset.

Sub-projects 3.2-3.8 built the working backend gradually: PostgreSQL storage, core read API, richer statistics, provider browsing, filtered CSV export, trend statistics, operational refresh, and final validation/demo readiness.

Sub-project 3.10 reorganized that backend into a clearer structure and added database readiness checks, simple logging, centralized database-error handling, and focused pytest coverage.

Sub-project 3.11 added a scheduler-ready MYH source-check foundation, local source-status manifest, source-check operation endpoints, refresh metadata, a manual source-check script, and focused tests that do not depend on live internet access.

## Technology choices

The backend uses:

- PostgreSQL for SQL storage,
- psycopg 3 for PostgreSQL access,
- FastAPI for the API,
- raw SQL for queries,
- Pydantic/FastAPI response models where they make JSON responses easier to understand,
- pytest for focused backend tests.

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
    services/
      common.py              shared filters and SQL helpers
      applications.py        application browsing and lookup queries
      stats.py               statistics and trend queries
      providers.py           provider browsing queries
      export.py              CSV export query and serializer
      health.py              database readiness checks
      source_check.py        MYH source-page check and manifest helpers
  runtime/
    README.md                explains local generated runtime files
  sql/
    schema.sql
    indexes.sql
  scripts/
    load_curated_data.py
    validate_database.py
    smoke_test_api.py
    demo_api.py
    check_source_status.py
  tests/
    test_check_source_status_script.py
    test_filter_helpers.py
    test_health_service.py
    test_operations_routes.py
    test_routes.py
    test_schemas_and_export.py
    test_source_check_service.py
```

`main.py` should stay small. New endpoint work should normally go into a router, with database/query or operation logic placed in a service module. This keeps the backend ready for protected operations, React dashboard work, and the ML extension planned after 3.11.

## Install dependencies

From `part_3`, use the Python environment you normally run this project with:

```bash
pip install -r backend/requirements.txt
```

## Configure PostgreSQL connection

Set `DATABASE_URL` before running database scripts or database-backed API endpoints.

Windows PowerShell:

```powershell
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/myh_applications"
```

macOS/Linux:

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/myh_applications"
```

Adjust user, password, host, port, and database name to match your local PostgreSQL setup.

## Load the curated CSV

From `part_3`:

```bash
python backend/scripts/load_curated_data.py --csv-path ../path/to/myh_curated_applications_2020_2025.csv
```

By default, the loader runs `schema.sql` and `indexes.sql` first. That recreates the tables, then loads the lookup rows and application rows. The API refresh endpoint uses the same loading helper.

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
- add protected admin operations.

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
- recreates the current PostgreSQL schema,
- reloads lookup tables and applications,
- includes source-check metadata when a manifest is available,
- does not download or replace source Excel files.

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

The smoke test checks the root endpoint, `/health`, `/health/db`, `/operations/source-status`, refresh, core browsing/statistics/provider/export endpoints, and important guardrails.

## 3.11 scope boundary

Implemented in 3.11:

- MYH source-check service,
- local JSON manifest support,
- `GET /operations/source-status`,
- `POST /operations/check-source`,
- refresh response metadata and optional recent-source-check guardrail,
- manual `check_source_status.py` script,
- focused tests for source-check logic and operation routes,
- README/control-file updates.

Not implemented in 3.11:

- React frontend,
- ML extension,
- protected admin write operations,
- authentication or user accounts,
- automatic source-file download and curated CSV replacement,
- production scheduler or background worker,
- ORM conversion.
