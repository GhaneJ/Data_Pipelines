# Part 3 — SQL Storage and API Service

## Purpose

Part 3 turns the curated Part 2 MYH applications dataset into a small internal data service.

The project shows the path from a trusted curated dataset to PostgreSQL storage, a FastAPI API, protected admin metadata operations, a React + TypeScript dashboard, cross-cutting middleware/error handling, database-backed authentication, scoped machine API keys, provider-owned submissions, admin review workflow, authenticated workspaces, and a production-grade MYH source-monitoring and refresh pipeline. The remaining roadmap can add a small explainable ML layer. The implementation stays practical and explainable while using professional structure where it solves real project problems.

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

Sub-project 3.20 upgrades the earlier source-check idea into a database-backed MYH source-monitoring and refresh pipeline. Admins can discover official downloadable MYH result workbooks, receive notifications for new/changed files, download and hash source files into local runtime storage, validate Tabell 3-style data, and import only affected official source years atomically. Provider-created submissions remain separate workflow data and are never inserted into the official historical `applications` table.

Sub-project 3.12 added a protected admin write use case: local application notes stored in a separate metadata table. Admin notes do **not** modify the curated MYH source data. Sub-project 3.15 added the central RBAC shape, and Sub-project 3.15.1 upgrades that boundary to database-backed users, hashed passwords, issued opaque bearer access tokens, token expiry, logout/revocation, and database-backed role authorization. Sub-project 3.16 adds database-backed API keys for machine/client access to protected exports. Sub-project 3.17 adds provider-authenticated application submission CRUD in a separate workflow table.

Sub-project 3.12.1 adds safe database seeder/startup initialization. The PostgreSQL database itself must already exist, and `DATABASE_URL` must point to it. When the FastAPI app starts, the backend safely checks/creates all project-managed tables and indexes through code. Startup does not reload, truncate, delete, or overwrite curated application data or admin notes.

Sub-project 3.13 adds a React + TypeScript dashboard under `frontend/`. It consumes public backend endpoints for health, database readiness, statistics, trends, filtered application browsing, and application detail. Protected admin-note endpoints are intentionally not exposed in the public dashboard.

Sub-project 3.14 adds request IDs, safe request logging, and standardized error envelopes. Sub-project 3.15 added centralized RBAC foundations. Sub-project 3.15.1 replaces the transitional environment-token identity source with PostgreSQL auth users, salted PBKDF2 password hashes, database-issued opaque bearer access tokens, hashed token storage, expiry, logout/revocation, `/auth/login`, database-backed `/auth/whoami`, and admin/provider role checks. Provider submission CRUD is implemented in 3.17 and admin review workflow is implemented in 3.18. Authenticated frontend workspace, OAuth/SSO/MFA, and ML remain outside this sub-project. API keys are implemented separately in 3.16 and do not replace user login sessions.

## Implementation principles

- Use PostgreSQL as the database.
- Use FastAPI for the backend API.
- Use psycopg 3 for PostgreSQL access.
- Use raw SQL for database queries.
- Do not use an ORM.
- Keep endpoint behavior backward compatible unless a real bug is found.
- Add structure only when it improves maintainability, validation, operations, or later roadmap work.
- Keep generated runtime files and internal handoff/control files outside Git tracking.

## Current project shape after Sub-project 3.20

Sub-project 3.10 reorganized the backend into routers and services, added database readiness checks, logging, centralized database-error handling, and focused pytest coverage.

Sub-project 3.11 added a modest scheduled-source-check foundation and refresh metadata upgrade. Sub-project 3.12 added protected admin notes as a safe write-side use case. Sub-project 3.12.1 added safe startup schema initialization with a single SQL schema source of truth. Sub-project 3.13 added the React + TypeScript visualization dashboard and minimal local-development CORS support for the Vite dev server. Sub-project 3.14 added request-context middleware, request logging middleware, and centralized safe error responses. Sub-project 3.15.1 adds database-backed login sessions and role-based authorization for admin and provider principals. Sub-project 3.16 adds database-backed API keys for machine access, scoped `X-API-Key` dependencies, admin-only key management, and API-key protection for CSV exports. Sub-project 3.17 adds provider-only submission CRUD for draft and submitted provider proposals. Sub-project 3.18 adds admin-authenticated review and decision workflow for submitted provider proposals. Sub-project 3.19 connects those backend capabilities to authenticated frontend workspaces. Sub-project 3.20 adds database-backed MYH source monitoring, admin notifications, safe workbook download, validation, atomic official-source import, and an admin operations page.

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
      api_keys/
        __init__.py
        dependencies.py          # X-API-Key parsing and scope dependencies
        key_utils.py             # opaque API key generation, hashing, prefixing
        models.py                # API key request/response/principal models
        repositories.py          # API key SQL helpers
        routes.py                # /admin/api-keys management endpoints
      provider_submissions/
        __init__.py
        dependencies.py          # provider bearer identity for submissions
        models.py                # provider submission request/response models
        repositories.py          # provider submission SQL helpers
        routes.py                # /provider/submissions CRUD endpoints
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
      upgrade_3_16_api_keys.sql    # historical 3.16 upgrade reference; startup schema covers current DB
    tests/
      test_admin_auth.py
      test_api_key_dependencies.py
      test_api_key_repositories.py
      test_api_key_routes.py
      test_api_key_utils.py
      test_auth_dependencies.py
      test_auth_routes.py
      test_admin_notes_service.py
      test_admin_routes.py
      test_check_source_status_script.py
      test_database_seeder.py
      test_error_handlers.py
      test_export_api_key_protection.py
      test_filter_helpers.py
      test_middleware.py
      test_health_service.py
      test_load_curated_data.py
      test_operations_routes.py
      test_provider_submission_routes.py
      test_provider_submissions_repositories.py
      test_provider_submissions_schema.py
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

Local admin/auth/API-key tables:

```text
application_notes
auth_users
auth_access_tokens
api_keys
```

The `applications` table remains the central curated-data table. Repeated high-value fields such as provider, education area, location, decision, principal type, and study form are represented through lookup tables. `application_notes`, `auth_users`, `auth_access_tokens`, `api_keys`, `provider_application_submissions`, and `provider_submission_review_events` are separate local system/workflow tables and do not overwrite source data.

Database initialization has a strict separation of responsibilities:

```text
backend/sql/schema.sql        safe table definitions, used by startup and loader
backend/sql/indexes.sql       safe index definitions, used by startup and loader
backend/sql/reset_schema.sql  explicit curated-data reset, used only by loader/refresh
```

The FastAPI startup seeder runs the safe schema and index files and seeds the fixed decision lookup values with `ON CONFLICT`. It never runs `reset_schema.sql` and never reloads the curated CSV. The loader/refresh workflow uses `reset_schema.sql` explicitly before reloading curated lookup rows and application rows from CSV. `application_notes`, `auth_users`, `auth_access_tokens`, `api_keys`, `provider_application_submissions`, and `provider_submission_review_events` are preserved across curated-data reloads.


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
- admin-only MYH source monitoring, source-file records, notifications, and refresh/import runs,
- protected admin notes attached to applications,
- record access,
- filtered and paginated browsing,
- grouped statistics,
- provider browsing,
- filtered CSV export protected by scoped API keys,
- trend statistics over `source_year`,
- one admin-controlled operational refresh endpoint routed through the robust refresh service.

Implemented endpoints:

```text
GET  /
GET  /health
GET  /health/db
GET  /admin/source-monitor/status
POST /admin/source-monitor/check
GET  /admin/source-files
GET  /admin/source-files/{source_file_id}
POST /admin/source-files/{source_file_id}/download
POST /admin/source-files/{source_file_id}/import
GET  /admin/refresh-runs
GET  /admin/refresh-runs/{refresh_run_id}
GET  /admin/notifications
POST /admin/notifications/{notification_id}/read
POST /admin/notifications/{notification_id}/resolve
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
POST /admin/api-keys
GET  /admin/api-keys
POST /admin/api-keys/{key_id}/revoke
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

3.15 uses this foundation for token authentication and RBAC. 3.16 reuses it for scoped API-key failures and protected CSV export access.

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

## MYH source monitoring and refresh operations

Sub-project 3.20 replaces the older toy source-status/refresh path with an admin-only operations feature. It uses code-managed PostgreSQL tables for MYH source check runs, detected source files, refresh/import runs, and admin notifications. Startup creates/updates these objects through the existing safe seeder path; no manual SQL should be run.

The source monitor can:

- fetch the configured official MYH result page,
- parse official downloadable result files from page HTML,
- ignore unrelated and unsupported links such as PDFs,
- record new, changed, and known files in PostgreSQL,
- create unread admin notifications for new/changed files and refresh outcomes,
- download selected official workbooks into `backend/runtime/source_files/`,
- compute SHA256 for downloaded files,
- transform Tabell 3-style Excel/CSV input into the project's applications shape,
- validate required columns, normalized decisions, source years, duplicate `diarienummer`, and row counts,
- import official rows atomically by replacing only affected `source_year` values,
- leave users, sessions, API keys, provider submissions, review events, and notifications untouched.

Provider-created submissions from the authenticated provider workflow remain separate workflow data. They are never inserted into the official historical `applications` table.

Environment variables:

```text
PART3_SOURCE_MONITOR_ENABLED=false
PART3_SOURCE_MONITOR_INTERVAL_MINUTES=360
PART3_SOURCE_MONITOR_RUN_ON_STARTUP=false
PART3_REFRESH_AUTO_IMPORT=false
PART3_MYH_SOURCE_PAGE_URL=https://www.myh.se/yrkeshogskolan/resultat-ansokningsomgangar/resultat-for-program
PART3_SOURCE_DOWNLOAD_DIR=backend/runtime/source_files
PART3_PROCESSED_OUTPUT_DIR=backend/runtime/processed
```

The scheduler is disabled by default and is also disabled in tests. By default, scheduled checks only detect source files and notify admins. Automatic import requires `PART3_REFRESH_AUTO_IMPORT=true` and should remain off for normal local validation.

Admin endpoints:

```text
GET    /admin/source-monitor/status
POST   /admin/source-monitor/check
GET    /admin/source-files
GET    /admin/source-files/{source_file_id}
POST   /admin/source-files/{source_file_id}/download
POST   /admin/source-files/{source_file_id}/import
GET    /admin/refresh-runs
GET    /admin/refresh-runs/{refresh_run_id}
GET    /admin/notifications
POST   /admin/notifications/{notification_id}/read
POST   /admin/notifications/{notification_id}/resolve
POST   /refresh
```

`POST /refresh` is kept for compatibility, but it now requires an admin bearer session and routes through the robust refresh service. Public users, providers, and export-only API keys cannot trigger source checks, downloads, imports, or refreshes.

Generated runtime files are local machine state and should not be committed:

```text
backend/runtime/source_files/
backend/runtime/processed/
backend/runtime/*.xlsx
backend/runtime/*.xls
backend/runtime/*.csv
backend/runtime/*.parquet
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

This is a real internal database-backed auth system for the project. It is intentionally not OAuth, SSO, MFA, JWT, or enterprise IAM. API keys are now implemented as a separate machine/client access system in 3.16. Provider submission CRUD is implemented in 3.17 and admin review/decision workflow is implemented in 3.18. Authenticated React admin/provider workspaces remain later roadmap steps.

## Database-backed API keys for machine access

Sub-project 3.16 adds API keys as a separate machine/client authentication mechanism. They do **not** replace `/auth/login`, admin/provider bearer sessions, or role-based user authorization. Human users still authenticate with:

```text
Authorization: Bearer <database-issued-access-token>
```

Machine clients use:

```text
X-API-Key: <database-issued-api-key>
```

API keys are stored in PostgreSQL table `api_keys`. Raw API keys are generated with high entropy, returned only once during creation, and never stored. The database stores only `key_hash`, plus safe metadata such as `name`, `description`, `key_prefix`, `scopes`, `expires_at`, `revoked_at`, `created_by_user_id`, and `last_used_at`. API responses never expose `key_hash`, and list/revoke responses never expose the raw key.

The API key scope model is intentionally simple and explainable. Scopes are stored as comma-separated text; the required scope for CSV export is:

```text
export:read
```

Optional future-oriented scope names reserved in code are `stats:read` and `refresh:run`, but 3.16 only protects `GET /export/applications`. Public read/dashboard endpoints remain public:

```text
GET /health
GET /health/db
GET /applications
GET /applications/{diarienummer}
GET /providers
GET /providers/{provider_id}/applications
GET /stats/...
```

Admin-only API key management endpoints require a database-issued admin bearer token:

```text
POST /admin/api-keys
GET  /admin/api-keys
POST /admin/api-keys/{key_id}/revoke
```

Example creation request:

```bash
curl -X POST "http://127.0.0.1:8000/admin/api-keys" \
  -H "Authorization: Bearer <admin-access-token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Local export client","description":"Local CSV export testing","scopes":["export:read"],"expires_in_days":30}'
```

The creation response includes `api_key` once. Store it locally; it cannot be retrieved later. Listing API keys returns only safe metadata such as id, name, key prefix, scopes, active/revoked state, expiry, creation time, and last-used time.

API-key failures use the same standardized 3.14 error envelope as the rest of the API. Missing, malformed, invalid, expired, or revoked keys return 401. A valid key without `export:read` returns 403. Success and failure responses keep `X-Request-ID`, and error bodies include the same request id. Logs must not include raw API keys, API key hashes, bearer tokens, or passwords.

This is an internal API-key system for this portfolio project. It is not OAuth, SSO, MFA, JWT, an API gateway, or enterprise IAM.


## Provider application submission and admin review workflow

Sub-project 3.17 added provider-owned application submission CRUD. Sub-project 3.18 adds the admin review and decision workflow on top of it. Provider-created submissions are stored in `provider_application_submissions`, a separate write-side workflow table from the historical curated `applications` table. Admin approval is a workflow decision only; it does **not** insert, update, delete, or promote rows in the curated historical MYH `applications` table.

Provider submission routes require a database-issued provider bearer session:

```text
Authorization: Bearer <database-issued-provider-access-token>
```

Admin review routes require a database-issued admin bearer session:

```text
Authorization: Bearer <database-issued-admin-access-token>
```

API keys are not valid for provider CRUD or admin review routes. API keys remain separate machine credentials for `GET /export/applications` with `export:read`. Admin bearer tokens are not provider sessions, provider bearer tokens are not admin sessions, and `X-Admin-Token` is not accepted.

Provider endpoints:

```text
POST   /provider/submissions
GET    /provider/submissions
GET    /provider/submissions/{submission_id}
PATCH  /provider/submissions/{submission_id}
DELETE /provider/submissions/{submission_id}
POST   /provider/submissions/{submission_id}/submit
```

Admin review endpoints:

```text
GET  /admin/provider-submissions
GET  /admin/provider-submissions/{submission_id}
GET  /admin/provider-submissions/{submission_id}/events
POST /admin/provider-submissions/{submission_id}/start-review
POST /admin/provider-submissions/{submission_id}/request-changes
POST /admin/provider-submissions/{submission_id}/approve
POST /admin/provider-submissions/{submission_id}/reject
```

Provider submission statuses after 3.18:

```text
draft
submitted
under_review
needs_changes
approved
rejected
```

Allowed transitions are deliberately explicit:

```text
draft -> submitted                  provider submit
submitted -> under_review            admin start review
submitted -> needs_changes           admin request changes
submitted -> approved                admin approve
submitted -> rejected                admin reject
under_review -> needs_changes        admin request changes
under_review -> approved             admin approve
under_review -> rejected             admin reject
needs_changes -> submitted           provider resubmit
```

Providers can update their own `draft` and `needs_changes` submissions. Providers can hard-delete only their own `draft` submissions. Providers cannot edit or delete `submitted`, `under_review`, `approved`, or `rejected` submissions. Providers cannot patch `status`, ownership fields, timestamps, or review fields directly. Reading another provider's submission returns 404 to avoid leaking record existence.

Admins can list the review queue, read any provider submission, start review, request changes, approve, reject, and inspect review/status-transition events. Review metadata is stored on the submission (`review_started_at`, `reviewed_by_user_id`, `reviewed_at`, and `review_notes`) and review history is stored in `provider_submission_review_events` with actor, action, from/to status, notes, and timestamp.

The database upgrade is code-managed and non-destructive. Existing 3.17 local databases are upgraded by `ensure_database_ready()` through application code: the old `draft/submitted` status constraint is replaced with the 3.18 status constraint, review metadata columns are added, the review event table is created, and review indexes are created. No manual table, column, constraint, or index creation is required; no destructive reset is required; curated data, admin notes, auth users, access tokens, API keys, and existing provider submissions are preserved.

Admin review failures use the same 3.14 error envelope and request ID behavior as the rest of the backend. Invalid workflow transitions return 409 Conflict. Missing/invalid bearer auth returns 401. Wrong roles return 403. Missing submissions return 404. Success and failure responses include `X-Request-ID`, and error bodies include the same request id.

Local validation commands from repository root:

```bash
python -m compileall part_3/backend/app part_3/backend/scripts
python -m pytest part_3/backend/tests
python part_3/backend/scripts/demo_api.py --print-only
```

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

`GET /export/applications` supports filtered CSV downloads with assignment-style examples. Since 3.16, it requires `X-API-Key` with `export:read`:

```text
GET /export/applications?year=2024&decision=approved
GET /export/applications?provider=KYH
GET /export/applications?provider_id=1
```

Trend endpoints support `year_from` and `year_to`. Decision trends can be filtered by `decision`, region trends by `region` or `lan`, and education-area trends by `education_area`. Region and education-area trends also support `limit` to return top groups for presentation or charting.

## Operational refresh

Sub-project 3.20 keeps `POST /refresh` as a compatibility endpoint, but it is now admin-only and routes through the robust refresh service. Admins can also use the dedicated source-monitoring endpoints to check the MYH source page, download selected official files, validate them, and import only affected official source years.

Compatibility refresh from the existing curated CSV:

```bash
curl -X POST "http://127.0.0.1:8000/refresh" \
  -H "Authorization: Bearer <admin-token>"
```

Source-monitoring flow:

```bash
curl -X POST "http://127.0.0.1:8000/admin/source-monitor/check" \
  -H "Authorization: Bearer <admin-token>"

curl -X POST "http://127.0.0.1:8000/admin/source-files/<source_file_id>/download" \
  -H "Authorization: Bearer <admin-token>"

curl -X POST "http://127.0.0.1:8000/admin/source-files/<source_file_id>/import" \
  -H "Authorization: Bearer <admin-token>"
```

Refresh/import behavior:

- validates required columns, decisions, years, duplicates, and row counts,
- computes SHA256 for downloaded source files,
- records source check runs, detected source files, refresh runs, and admin notifications,
- uses transactions and rolls back failed imports,
- replaces only affected official source years for official source imports,
- preserves users, sessions, API keys, provider submissions, review events, and admin notifications.

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
http://127.0.0.1:8000/admin/source-monitor/status
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

## Expanded roadmap after 3.20

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
3.16 Database-Backed API Key Access System — completed
3.17 Provider Application Submission CRUD API — completed
3.18 Admin Review and Decision Workflow API — completed
3.19 Authenticated React Admin and Provider Workspace — completed
3.20 Scheduled MYH Source Monitoring, Admin Notifications, and Production-Grade Refresh Pipeline — completed
3.21 Small Explainable ML Extension
3.22 Final Integration, Presentation Update, and Submission Cleanup
```

Guiding rule:

```text
Vocational level means explainable and proportionate, not toy-like or artificially weak. Use normal professional structure when it improves correctness, maintainability, robustness, operations, or presentation value.
```

The React dashboard is implemented and consumes public read/statistics endpoints. Central token authentication, role-based authorization, and database-backed API keys are in place for backend routes. Provider submission CRUD, admin review workflow, authenticated React workspaces, and admin source-monitoring operations are implemented. ML remains planned for the next sub-project.

## Git policy

Commit by coherent logical change.

Do not commit:

```text
virtual environments
node_modules
.env files
database dumps
local runtime/generated files such as backend/runtime/source_files/, backend/runtime/processed/, and backend/runtime/source_status.json
internal handoff/control files
```

## Sub-project 3.19 authenticated workspace update

Sub-project 3.19 extends the Part 3 system from a public dashboard plus protected API workflows into a browser-usable authenticated workspace.

The important boundary is unchanged: the official historical `applications` table remains read-oriented MYH data loaded from the curated Part 2 dataset. Provider-created submissions remain separate workflow records and admin approval of a provider submission does not insert that record into `applications`.

### Human login, controlled signup, and machine access

Human users authenticate with the database-backed 3.15.1 bearer-session flow:

```text
Authorization: Bearer <database-issued-session-token>
```

Public visitors may request provider access through the controlled signup form. That creates a pending `user_registration_requests` row only. It does not create an active user and it does not log the applicant in. An admin must approve the request before a provider user is created and can log in.

Machine/API-client access remains separate:

```text
X-API-Key: <database-issued-api-key>
```

API keys are for scoped machine operations such as `GET /export/applications` with `export:read`. They are not used by the React human workspace and they do not grant admin or provider access.

### New backend capabilities

3.19 adds code-managed tables and indexes for:

```text
user_registration_requests
auth_admin_events
```

The backend exposes public controlled signup and admin-only registration/user-management routes:

```text
POST   /auth/registration-requests
GET    /admin/registration-requests
GET    /admin/registration-requests/{request_id}
POST   /admin/registration-requests/{request_id}/approve
POST   /admin/registration-requests/{request_id}/reject
GET    /admin/users
POST   /admin/users
GET    /admin/users/{user_id}
PATCH  /admin/users/{user_id}
POST   /admin/users/{user_id}/reset-password
POST   /admin/users/{user_id}/deactivate
POST   /admin/users/{user_id}/reactivate
GET    /admin/users/{user_id}/sessions
POST   /admin/users/{user_id}/sessions/{session_id}/revoke
```

Passwords, password hashes, session token hashes, API key hashes, and raw API keys are not returned by user-management responses.

### React workspace

The React app now includes:

```text
/login
/signup
/admin
/admin/users
/admin/signup-requests
/admin/provider-submissions
/admin/api-access
/admin/operations
/provider
/provider/submissions
/data
/data/applications
/data/stats
```

The frontend stores the human bearer token in `sessionStorage`, checks `/auth/whoami` on load, clears the session on logout or `401`, and never uses API keys for human login. Admin screens call admin-only backend routes; provider screens call provider-owned submission routes; the data explorer keeps using public read/statistics endpoints.

### Validation

Backend validation from the repository root:

```bash
python -m compileall part_3/backend/app part_3/backend/scripts
python -m pytest part_3/backend/tests
python part_3/backend/scripts/demo_api.py --print-only
```

Frontend validation from `part_3/frontend`:

```bash
npm install
npm run lint
npm test -- --run
npm run build
```


## Sub-project 3.20 source monitoring and refresh update

Sub-project 3.20 turns the refresh idea into an admin operations feature. The backend now has code-managed tables for `myh_source_check_runs`, `myh_source_files`, `myh_refresh_runs`, and `admin_notifications`. The frontend now has `/admin/operations` for source monitor status, detected source files, notifications, refresh history, request-ID-aware failures, and in-app confirmation before imports.

The official historical `applications` table remains distinct from provider-created workflow submissions. Official-source imports are validated and transactional. Provider submissions, review events, users, sessions, API keys, and notifications are not reset or promoted into historical MYH data.

Runtime downloads and processed outputs belong under `backend/runtime/source_files/` and `backend/runtime/processed/` and must not be committed.
