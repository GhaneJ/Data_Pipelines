# Part 3 — SQL Storage and API Service

## Purpose

Part 3 turns the curated Part 2 MYH applications dataset into a small internal data service.

The project shows the full path from a trusted curated CSV to PostgreSQL storage and a FastAPI API that another system, analyst, or presentation layer can consume. The implementation stays practical and explainable: PostgreSQL, FastAPI, psycopg 3, raw SQL, and a compact backend structure.

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

The raw Excel files are not loaded directly by the Part 3 API. They belong to the Part 2 transformation journey. Part 3 operationalizes the finished curated dataset.

## Implementation principles

- Keep the implementation direct and easy to explain.
- Use PostgreSQL as the database.
- Use FastAPI for the backend API.
- Use psycopg 3 for PostgreSQL access.
- Use raw SQL for database queries.
- Do not use an ORM.
- Keep comments and docstrings concise and useful.
- Add structure only when it solves a real project need.
- Keep commits focused on coherent project changes.
- Keep internal handoff/control files outside Git tracking.

## Current backend shape after Sub-project 3.8

The backend remains intentionally compact:

```text
part_3/
  README.md
  .gitignore
  backend/
    README.md
    requirements.txt
    app/
      __init__.py
      database.py
      main.py
      queries.py
      schemas.py
    scripts/
      demo_api.py
      load_curated_data.py
      smoke_test_api.py
      validate_database.py
    sql/
      schema.sql
      indexes.sql
```

This is enough for the current SQL + API layer. Routers, service layers, frontend folders, authentication modules, background workers, or schedulers should only be added later if they clearly improve the final project.

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

Traceability fields from the curated dataset are preserved, including:

```text
source_year
source_file
source_sheet
source_row
diarienummer
```

## API story

The API reads from PostgreSQL and provides:

- service health/status checks,
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

`POST /refresh` reloads PostgreSQL from the existing curated CSV. It validates required columns and expected dataset assumptions, recreates the current schema, reloads lookup tables and applications, and returns a short JSON summary. It does not fetch new MYH files or rerun the full Part 2 notebook pipeline.

Recommended pagination defaults:

```text
limit=50
offset=0
max_limit=500
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

In another terminal, run the final smoke test:

```bash
python backend/scripts/smoke_test_api.py
```

For a presentation-friendly endpoint sequence, run:

```bash
python backend/scripts/demo_api.py
```

To include the operational refresh call in the demo sequence:

```bash
python backend/scripts/demo_api.py --include-refresh
```

## What the project does not do

The Part 3 backend does not currently include:

```text
authentication or user accounts
frontend/dashboard code
background workers or schedulers
production deployment setup
raw MYH Excel fetching
full Part 2 notebook reruns through the API
POST /ingestion/run
```

This boundary is intentional. The final API already demonstrates SQL storage, record access, filtering, browsing, statistics, provider browsing, export, trends, and refresh in a way that is still understandable.

## Optional next direction

After Sub-project 3.8, the main backend/API path is demo-ready. The next step should be final presentation preparation: choose a clear video flow, rehearse the local validation commands, and decide whether a very small optional dashboard or final polish layer would actually improve the presentation.

Do not add a frontend, authorization layer, or second operational endpoint unless it clearly adds value and remains explainable.

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

Good commit examples:

```text
docs(part-3): define architecture and implementation plan
chore(part-3): ignore local runtime artifacts
feat(part-3): add PostgreSQL schema and indexes
feat(part-3): load and validate curated dataset
feat(part-3): add core application endpoints
feat(part-3): add extended statistics endpoints
feat(part-3): add provider browsing endpoints
feat(part-3): add filtered CSV export endpoint
feat(part-3): add trend statistics endpoints
feat(part-3): add operational refresh endpoint
test(part-3): add final API demo validation flow
docs(part-3): polish final API documentation
```
