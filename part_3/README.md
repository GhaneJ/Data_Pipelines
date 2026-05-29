# Part 3 — SQL Storage and API Service

## Purpose

Part 3 turns the curated Part 2 MYH applications dataset into a small internal data service.

The project shows the path from a trusted curated dataset to PostgreSQL storage, a FastAPI API, protected admin metadata operations, a React + TypeScript dashboard that consumes the public API, a cross-cutting middleware/error foundation, and now database-backed authentication with issued bearer tokens and role-based authorization. The remaining roadmap adds API keys, provider/admin workflows, operational hardening, and a small explainable ML layer in staged steps. The implementation stays practical and explainable while using normal professional structure where it solves real project problems.

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

Sub-project 3.12 added a protected admin write use case: local application notes stored in a separate metadata table. Admin notes do **not** modify the curated MYH source data. Sub-project 3.15 added the central RBAC shape, and Sub-project 3.15.1 upgrades that boundary to database-backed users, hashed passwords, issued opaque bearer access tokens, token expiry, logout/revocation, and database-backed role authorization.

Sub-project 3.12.1 adds safe database seeder/startup initialization. The PostgreSQL database itself must already exist, and `DATABASE_URL` must point to it. When the FastAPI app starts, the backend safely checks/creates all project-managed tables and indexes through code. Startup does not reload, truncate, delete, or overwrite curated application data or admin notes.

Sub-project 3.13 adds a React + TypeScript dashboard under `frontend/`. It consumes public backend endpoints for health, database readiness, statistics, trends, filtered application browsing, and application detail. Protected admin-note endpoints are intentionally not exposed in the public dashboard.

Sub-project 3.14 adds request IDs, safe request logging, and standardized error envelopes. Sub-project 3.15 added centralized RBAC foundations. Sub-project 3.15.1 replaces the transitional environment-token identity source with PostgreSQL auth users, salted PBKDF2 password hashes, database-issued opaque bearer access tokens, hashed token storage, expiry, logout/revocation, `/auth/login`, database-backed `/auth/whoami`, and admin/provider role checks. It does not implement API keys, provider CRUD, admin review workflow, authenticated frontend workspace, OAuth/SSO/MFA, or ML.

## Implementation principles

- Use PostgreSQL as the database.
- Use FastAPI for the backend API.
- Use psycopg 3 for PostgreSQL access.
- Use raw SQL for database queries.
- Do not use an ORM.
- Keep endpoint behavior backward compatible unless a real bug is found.
- Add structure only when it improves maintainability, validation, operations, or later roadmap work.
- Keep generated runtime files and internal handoff/control files outside Git tracking.

## Current project shape after Sub-project 3.15.1

Sub-project 3.10 reorganized the backend into routers and services, added database readiness checks, logging, centralized database-error handling, and focused pytest coverage.

Sub-project 3.11 added a modest scheduled-source-check foundation and refresh metadata upgrade. Sub-project 3.12 added protected admin notes as a safe write-side use case. Sub-project 3.12.1 added safe startup schema initialization with a single SQL schema source of truth. Sub-project 3.13 added the React + TypeScript visualization dashboard and minimal local-development CORS support for the Vite dev server. Sub-project 3.14 added request-context middleware, request logging middleware, and centralized safe error responses. Sub-project 3.15.1 adds database-backed login sessions and role-based authorization for admin and provider principals.

```text
part_3/
  README.md
  pyproject.toml
  frontend/
    README.md
    package.json
    index.html
    vite.config.ts
    src/
      App.tsx
      main.tsx
      styles.css
      components/
        ApplicationsBrowser.tsx
        ApplicationDetailPanel.tsx
        BackendStatusPanel.tsx
        CategoryBars.tsx
        DecisionTrendChart.tsx
        StateMessage.tsx
        SummaryCards.tsx
        YearTrendChart.tsx
      hooks/
        useDashboardMetrics.ts
      services/
        api.ts
      test/
        setup.ts
  backend/
    README.md
    requirements.txt
    app/
      __init__.py
      database.py
      dependencies.py
      exception_handlers.py       # central safe API error handlers
      logging_config.py
      main.py
      queries.py                 # compatibility exports for older imports
      schemas.py
      auth/
        __init__.py
        dependencies.py          # bearer auth and reusable RBAC dependencies
        models.py                # safe authenticated principal and roles
        password_hashing.py      # salted PBKDF2 password hashing
        repositories.py          # auth user/token SQL helpers
        routes.py                # /auth/login, /auth/whoami, /auth/logout
        token_store.py           # retired static-token compatibility guard
        tokens.py                # opaque token generation and hashing
      core/
        errors.py                # standard API error envelope helpers
      middleware/
        request_context.py       # X-Request-ID handling
        logging_middleware.py    # safe request logging
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
        database_seeder.py         # safe startup schema/index bootstrap
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
      reset_schema.sql             # explicit full-reload reset, never used by startup
      schema.sql                   # safe CREATE TABLE IF NOT EXISTS schema source
      indexes.sql                  # safe CREATE INDEX IF NOT EXISTS indexes
    tests/
      test_admin_auth.py
      test_auth_dependencies.py
      test_auth_routes.py
      test_admin_notes_service.py
      test_admin_routes.py
      test_check_source_status_script.py
      test_database_seeder.py
      test_error_handlers.py
      test_filter_helpers.py
      test_middleware.py
      test_health_service.py
      test_load_curated_data.py
      test_operations_routes.py
      test_routes.py
      test_schemas_and_export.py
      test_source_check_service.py
```

`main.py` remains app assembly and startup registration only. Route code lives in `backend/app/routers/`. Database-backed query/business logic lives in `backend/app/services/`. Response models remain in `schemas.py` because splitting small schemas further is still unnecessary.

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

Database initialization has a strict separation of responsibilities:

```text
backend/sql/schema.sql        safe table definitions, used by startup and loader
backend/sql/indexes.sql       safe index definitions, used by startup and loader
backend/sql/reset_schema.sql  explicit curated-data reset, used only by loader/refresh
```

The FastAPI startup seeder runs the safe schema and index files and seeds the fixed decision lookup values with `ON CONFLICT`. It never runs `reset_schema.sql` and never reloads the curated CSV. The loader/refresh workflow uses `reset_schema.sql` explicitly before reloading curated lookup rows and application rows from CSV. `application_notes` is preserved across curated-data reloads.


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

`GET /health/db` checks database readiness for real API use. It verifies that the database connection works, required tables exist, the `applications` table has rows, and key lookup tables have rows. The React dashboard uses this endpoint to show whether the database is ready for a demo.


## Request IDs, logging, and safe error responses

Sub-project 3.14 adds a cross-cutting backend foundation that future auth/API-key/workflow features can reuse.

Request ID behavior:

- callers may send `X-Request-ID`,
- the backend generates a UUID request ID when the header is missing or unsafe,
- the request ID is stored on `request.state`,
- every response includes `X-Request-ID`,
- API error responses include the same request ID in the JSON body,
- request logs include the request ID.

Request logging records method, path, safe query parameters, status code, duration in milliseconds, client host, and request ID. It does not log request bodies, response bodies, admin tokens, authorization headers, API keys, or token-like query values.

Standard API errors now use this envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "request_id": "demo-request-123"
  },
  "detail": "Request validation failed."
}
```

The top-level `detail` field is kept for compatibility with existing FastAPI/browser helpers, while new code should use the `error` object. The handlers preserve important status codes such as 400, 401, 403, 404, 422, 500, and 503, and avoid exposing stack traces or internal database exception details.

3.15 uses this foundation for token authentication and RBAC. API keys are still not implemented; they are planned for 3.16.

## React + TypeScript dashboard

Sub-project 3.13 adds the frontend under:

```text
frontend/
```

The dashboard is a Vite + React + TypeScript app. It is presentation-oriented, but it uses real public API endpoints instead of hardcoded demo data.

Frontend features:

- backend/API status panel using `/health`,
- database readiness panel using `/health/db`,
- summary cards based on `/stats/by-year` and `/stats/by-decision`,
- yearly application trend chart,
- decision trend chart,
- region and education-area visualizations,
- bounded filterable application browser using `/applications`,
- selected application detail panel using `/applications/{diarienummer}`,
- loading, empty, and error states for demo safety.

Protected admin-note endpoints are not called by the React dashboard. They remain backend/API features tested separately through database-issued admin bearer tokens from `/auth/login`.

### Start the frontend

Start the backend first from `part_3`, with `DATABASE_URL` configured:

```bash
python -m uvicorn backend.app.main:app --reload
```

Then start the frontend from `part_3/frontend`:

```bash
npm install
npm run dev
```

The local Vite URL is normally:

```text
http://localhost:5173
```

The frontend uses this default backend URL:

```text
http://127.0.0.1:8000
```

Override it with a local environment variable when needed:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

PowerShell example:

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm run dev
```

### Frontend validation

From `part_3/frontend`:

```bash
npm install
npm run build
npm run lint
npm test
```

`npm run lint` currently runs TypeScript type-checking through `tsc --noEmit`, keeping the frontend validation lightweight and explainable.

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

## Authentication and role-based authorization

Sub-project 3.15.1 upgrades the 3.15 RBAC foundation into a real internal database-backed authentication system. Users live in PostgreSQL, passwords are stored only as salted PBKDF2-HMAC-SHA256 hashes, and access is granted with opaque bearer tokens issued by `/auth/login`. Raw bearer tokens are returned once at login; only SHA-256 token hashes are stored in `auth_access_tokens`.

Auth tables:

```text
auth_users
auth_access_tokens
```

Bootstrap environment variables are used only to create safe local database users when the backend starts. They are not request-time credentials:

```text
PART3_BOOTSTRAP_ADMIN_USERNAME=admin
PART3_BOOTSTRAP_ADMIN_PASSWORD=admin-password
PART3_BOOTSTRAP_ADMIN_DISPLAY_NAME=Local Admin

PART3_BOOTSTRAP_PROVIDER_USERNAME=provider
PART3_BOOTSTRAP_PROVIDER_PASSWORD=provider-password
PART3_BOOTSTRAP_PROVIDER_DISPLAY_NAME=Local Provider
PART3_BOOTSTRAP_PROVIDER_ID=999999
```

Bootstrap behavior is idempotent. If a user already exists, startup leaves it unchanged and does not silently overwrite the password. The API can start without bootstrap variables, but login only works if users already exist in `auth_users`. Passwords and raw tokens must not appear in logs.

Supported roles:

```text
admin
provider
```

Login flow:

```text
POST /auth/login
Authorization: Bearer <database-issued-access-token>
GET /auth/whoami
POST /auth/logout
```

`POST /auth/login` accepts a username/password and returns:

```json
{
  "access_token": "returned-once",
  "token_type": "bearer",
  "expires_at": "2026-05-29T..."
}
```

`GET /auth/whoami` requires a valid database-issued bearer token and returns only safe identity fields. Admin example:

```json
{
  "subject": "user:<uuid>",
  "username": "admin",
  "display_name": "Local Admin",
  "role": "admin",
  "provider_id": null
}
```

Provider example:

```json
{
  "subject": "user:<uuid>",
  "username": "provider",
  "display_name": "Local Provider",
  "role": "provider",
  "provider_id": "999999"
}
```

`POST /auth/logout` revokes the current token. A logged-out, expired, missing, malformed, or unknown token returns a standardized 401 error envelope. A valid provider token on an admin-only route returns a standardized 403 error envelope. Auth success and failure responses include `X-Request-ID`, and the same request ID appears inside the `error` object on failures.

This is a real internal database-backed auth system for the project. It is intentionally not OAuth, SSO, MFA, JWT, or enterprise IAM. API keys are not part of 3.15.1 and are planned for 3.16. Provider CRUD, admin review workflow, and authenticated React admin/provider workspaces are also later roadmap steps.

## Protected admin application notes

Sub-project 3.12 added one small write-side feature under `/admin`: local notes linked to application `diarienummer` values. Public read endpoints remain public. Admin note text is only available through protected `/admin` endpoints. Sub-project 3.15.1 requires a database-issued admin bearer token for these routes.

Admin note endpoints:

```text
GET    /admin/applications/{diarienummer}/notes
POST   /admin/applications/{diarienummer}/notes
PUT    /admin/notes/{note_id}
PATCH  /admin/notes/{note_id}
DELETE /admin/notes/{note_id}
```

Admin requests use:

```text
Authorization: Bearer <database-issued-admin-access-token>
```

The previous static local admin header is no longer accepted. Missing or invalid bearer credentials return 401. A valid provider token on these admin-only routes returns 403.

Example flow:

```bash
curl -X POST "http://127.0.0.1:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin-password"}'

curl -H "Authorization: Bearer <admin-access-token>" \
  "http://127.0.0.1:8000/admin/applications/MYH%202024%2F1/notes"

curl -H "Authorization: Bearer <admin-access-token>" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{"note_text":"Check this application before the demo."}' \
  "http://127.0.0.1:8000/admin/applications/MYH%202024%2F1/notes"

curl -H "Authorization: Bearer <admin-access-token>" \
  -H "Content-Type: application/json" \
  -X PATCH \
  -d '{"note_text":"Partially update the local note text."}' \
  "http://127.0.0.1:8000/admin/notes/1"

curl -H "Authorization: Bearer <admin-access-token>" \
  -X DELETE "http://127.0.0.1:8000/admin/notes/1"
```

The note table is `application_notes`. It stores local admin metadata only. It does not change `applications` or any MYH source file. The service validates that a `diarienummer` exists before writing or listing notes. `PUT` replaces the note text. `PATCH` supports partial update semantics; because the current model has one editable field, it updates `note_text` when provided and rejects an empty body with `400`.

Admin-token behavior:

- `Authorization: Bearer <database-issued-admin-access-token>` is required,
- missing, malformed, expired, revoked, or invalid bearer tokens return 401,
- valid provider credentials on admin-only routes return 403,
- static request-time admin headers no longer grant access.

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

`POST /refresh` still reloads PostgreSQL from the existing curated CSV. It validates required columns and expected dataset assumptions, runs the explicit curated-data reset, recreates the safe schema, reloads lookup tables and applications, and returns a JSON summary. Local `application_notes` rows are preserved.

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
python -m compileall backend/app backend/scripts
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

Start the API. The startup seeder requires `DATABASE_URL`, connects to the existing PostgreSQL database, and safely checks/creates project-managed tables and indexes before serving routes:

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
http://127.0.0.1:8000/does-not-exist
http://127.0.0.1:8000/applications?limit=wrong
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

## Expanded roadmap after 3.15

The assignment remains the baseline for required deliverables, but the assessor has allowed stronger additions when they remain explainable at vocational/YH-student level and improve the final project/demo value.

Current roadmap:

```text
3.10 Backend Structure and Robustness Foundation — completed
3.11 Scheduled MYH Source Check and Refresh Upgrade — completed
3.12 Protected Admin Operations and Safe Write Use Case — completed
3.12.1 Database Seeder Initialization — completed
3.13 React + TypeScript Visualization and Trend Dashboard — completed
3.14 Cross-cutting API Middleware Foundation — completed
3.15 Portfolio-Grade Token Authentication and Role-Based Authorization — completed as RBAC foundation
3.16 API Key Access System — next
3.17 Provider Application Submission CRUD API
3.18 Admin Review and Decision Workflow API
3.19 Authenticated React Admin and Provider Workspace
3.20 Scheduled POST/Refresh Operations Hardening
3.21 Small Explainable ML Extension
3.22 Final Integration, Presentation Update, and Submission Cleanup
```

Guiding rule:

```text
Vocational level means explainable and proportionate, not toy-like or artificially weak. Use normal professional structure when it improves correctness, maintainability, robustness, operations, or presentation value.
```

The React dashboard is implemented and consumes public read/statistics endpoints. Central token authentication and role-based authorization are now in place for backend routes. API keys, provider CRUD, admin review workflows, authenticated React workspaces, and ML are still not implemented yet; they are planned for later sub-projects.

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
