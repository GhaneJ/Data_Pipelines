# Part 3 — SQL Storage and API Service

## Purpose

Part 3 turns the curated Part 2 dataset into a small data service.

The goal is to show that the cleaned MYH application data can be stored in PostgreSQL, queried through SQL, and consumed through a FastAPI API. The solution should stay practical, readable, and explainable while still supporting a strong VG-level result.

## Source of truth

The curated CSV from Part 2 is the source of truth for Part 3:

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

The raw Excel files are not required for the first Part 3 implementation steps because the curated CSV is already the finished Part 2 output.

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

## Planned project shape

The project should grow in stages.

A possible final shape is:

```text
part_3/
  README.md
  .gitignore
  backend/
    app/
      main.py
      config.py
      db.py
      routers/
        applications.py
        providers.py
        stats.py
        exports.py
      schemas/
        applications.py
      sql/
        schema.sql
        indexes.sql
      scripts/
        load_curated_data.py
        validate_database.py
  frontend/
```

This full shape should not be created in one step. Each folder and file should be added when its layer is implemented.

## Database plan

The database should be normalized, but not over-normalized.

Planned core tables:

```text
applications
providers
education_areas
locations
decisions
principal_types
study_forms
```

No authentication/RBAC tables are part of the current database plan.

The `applications` table remains the central table. Repeated high-value fields such as provider, education area, location, decision, principal type, and study form can be moved into lookup tables. Smaller descriptive fields can stay directly in `applications` when a separate table would not add clear value.

The schema should preserve traceability fields from the curated dataset, including:

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

## Backend API plan

The API should primarily read from PostgreSQL and return JSON.

Core endpoints:

```text
GET /health
GET /applications
GET /applications/{diarienummer}
GET /stats/by-year
```

Useful VG-level endpoints:

```text
GET /providers
GET /providers/{provider_id}/applications
GET /stats/by-region
GET /stats/by-education-area
GET /stats/trends/approval-rate
GET /stats/trends/distance-vs-bound
GET /export/applications
```

`GET /applications` should support `limit` and `offset`.

Recommended filters:

```text
year
decision
region
municipality
provider
education_area
study_form
is_distance_based
is_approved
```

Recommended pagination defaults:

```text
limit=50
offset=0
max_limit=500
```

## Authentication/RBAC boundary

Authentication and role-based authorization are not part of the current implementation path. The Part 3 solution should first prove the database and read API over the curated dataset.

## Seed data plan

Seed data should not be added unless it has a clear purpose.

For Sub-project 3.2, no seed script is needed because the real curated CSV is loaded directly into PostgreSQL.

## Frontend plan

React should be added after the backend API is usable.

Planned pages:

```text
Applications table
Application detail page
Statistics dashboard
Providers page
```

Frontend features:

```text
pagination
selectable page size
filters
trend charts for 2020-2025
```

The frontend should show that the API can be consumed by another part of a system.

## Suggested implementation sequence

```text
3.1 Architecture and contracts
3.2 PostgreSQL schema, indexes, curated CSV loader, validation
3.3 Core FastAPI read API
3.4 Filters, statistics, trends, and exports
3.5 React frontend
3.6 Testing, documentation, and presentation readiness
```

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
feat(part-3): add statistics and export endpoints
feat(part-3): add React application table
```
