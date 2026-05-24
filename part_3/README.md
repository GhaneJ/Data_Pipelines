# Part 3 — SQL Storage and API Service

## Purpose

Part 3 turns the curated Part 2 dataset into a small data service.

The goal is to show that the cleaned MYH application data can be stored in PostgreSQL, queried through SQL, and consumed through a FastAPI API. The solution should stay practical, readable, and explainable while still supporting a strong final project direction.

## Source of truth

The curated CSV from Part 2 is the data source used for the Part 3 database load:

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

The raw Excel files are not required for the first Part 3 backend steps because the curated CSV is already the finished Part 2 output.

## Implementation principles

The project should be built gradually and only add structure when it is needed.

Principles:

- Keep the implementation direct and easy to explain.
- Use PostgreSQL as the database.
- Use FastAPI for the backend API.
- Use psycopg 3 for PostgreSQL access.
- Use raw SQL for database queries.
- Do not use an ORM.
- Use comments where they help explain project-specific logic.
- Prefer readable SQL and Python over generic abstractions.
- Add folders and modules only when the current implementation step needs them.
- Keep commits focused on coherent project changes.
- Keep internal handoff/control files outside Git tracking.

## Current backend shape after Sub-project 3.4

The backend is intentionally compact:

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
      load_curated_data.py
      smoke_test_api.py
      validate_database.py
    sql/
      schema.sql
      indexes.sql
```

This structure is enough for the current SQL + API layer. Routers, frontend folders, authentication modules, or other extra architecture should only be added later when they solve a real project need.

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

The schema preserves traceability fields from the curated dataset, including:

```text
source_year
source_file
source_sheet
source_row
diarienummer
```

## Indexing plan

Use simple indexes that support common filters and lookups:

```text
applications(diarienummer)
applications(source_year)
applications(decision_code)
applications(provider_id)
applications(education_area_id)
applications(location_id)
applications(study_form_id)
applications(source_year, decision_code)
providers(utbildningsanordnare)
locations(lan, kommun)
```

The first goal is understandable query performance, not advanced database optimization.

## Implemented API after Sub-project 3.4

The API reads from PostgreSQL and returns JSON responses.

Implemented endpoints:

```text
GET /health
GET /applications
GET /applications/{diarienummer}
GET /stats/by-year
GET /stats/by-region
GET /stats/by-education-area
GET /stats/by-decision
GET /providers
GET /providers/{provider_id}/applications
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

Provider browsing uses numeric `provider_id` values in path parameters. Provider names are still useful as query parameters, but they should not be used as path parameters because names may contain spaces, punctuation, Swedish characters, or organization suffixes.

Recommended pagination defaults:

```text
limit=50
offset=0
max_limit=500
```

## Next backend step: Sub-project 3.5

Sub-project 3.5 should add the filtered export API as the next backend capability:

```text
GET /export/applications
```

The export endpoint should support assignment-style and API-friendly examples such as:

```text
GET /export/applications?year=2024&decision=approved
GET /export/applications?provider=...
GET /export/applications?provider_id=...
```

CSV should be the main export format because it is practical, easy to demonstrate, and useful for API consumers who need downloadable filtered data.

3.5 should not repeat existing 3.3 or 3.4 endpoints as new features. It should build on them.

## Later staged direction

The project remains open for further ambition after the filtered export API:

```text
3.5 Filtered Export API and Backend Validation
3.6 Trend Statistics API
3.7 Operational Refresh / Ingestion Workflow
3.8 Frontend Foundation
3.9 Dashboard and Browsing Interface
3.10 Optional Authorization Layer
3.11 Final Validation, Demo Flow, and Submission Readiness
```

Trend statistics should build on the existing statistics endpoints and show development over `source_year`, for example trends by decision, region, or education area. This belongs after the filtered export API so 3.5 stays focused.

Operational endpoints belong after the export API and trend statistics are stable. The likely first operational endpoint is:

```text
POST /refresh
```

`POST /ingestion/run` should only be added if it has a distinct purpose from refresh, such as rebuilding from source inputs instead of reloading the existing curated dataset.

## Authentication and authorization boundary

Authentication and role-based authorization are not required by the assignment and are not part of the current backend implementation.

An authorization layer may be considered later as an optional ambition step, but it should stay separate from the core SQL/API work and should not weaken the explainability of the main data-service journey.

## Frontend direction

A frontend should be added only after the backend API is stable enough to consume.

Planned frontend direction:

```text
Applications table
Application detail page
Statistics dashboard
Providers page
Export controls
```

Frontend features can include:

```text
pagination
selectable page size
filters
charts for statistics
provider browsing
CSV export button
```

The frontend should show that the API can be consumed by another part of a system.

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
feat(part-3): add frontend API browsing foundation
```
