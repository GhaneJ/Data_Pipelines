# Part 3 Backend — PostgreSQL and FastAPI

This folder contains the Part 3 backend for storing and exposing the curated MYH applications dataset.

Sub-projects 3.2-3.8 built the working backend gradually: PostgreSQL storage, core read API, richer statistics, provider browsing, filtered CSV export, trend statistics, operational refresh, and final validation/demo readiness.

Sub-project 3.10 reorganized that backend into a clearer structure and added database readiness checks, simple logging, centralized database-error handling, and focused pytest coverage.

Sub-project 3.11 added a scheduler-ready MYH source-check foundation, local source-status manifest, source-check operation endpoints, refresh metadata, a manual source-check script, and focused tests that do not depend on live internet access. Sub-project 3.12 adds protected admin application notes as a small safe write-side use case. Sub-project 3.12.1 adds safe database seeder/startup initialization with SQL files as the single schema source of truth. Sub-project 3.13 adds minimal local-development CORS support so the React/Vite dashboard can call the public API from the browser. Sub-project 3.14 adds request IDs, safe request logging, and standardized API error envelopes. Sub-project 3.15 adds centralized RBAC foundations. Sub-project 3.15.1 upgrades authentication to PostgreSQL-backed users, hashed passwords, issued opaque bearer tokens, logout/revocation, and database-backed role authorization. Sub-project 3.16 adds database-backed API keys for machine/client access, admin-only API-key management, scoped `X-API-Key` dependencies, and API-key protection for CSV exports. Sub-project 3.17 adds provider-authenticated application submission CRUD in a separate workflow table. Sub-project 3.18 adds admin review workflow, 3.19 exposes the authenticated frontend workspace, and 3.20 adds database-backed MYH source monitoring, admin notifications, safe source-file download, validation, and atomic official-source imports.

## Technology choices

The backend uses:

- PostgreSQL for SQL storage,
- psycopg 3 for PostgreSQL access,
- FastAPI for the API,
- raw SQL for queries,
- Pydantic/FastAPI response models where they make JSON responses easier to understand,
- pytest for focused backend tests,
- narrow local-development CORS for the React dashboard,
- request-id middleware and safe request logging,
- standardized safe API error responses,
- database-backed bearer-token authentication and role-based authorization,
- database-backed API keys for scoped machine/client export access,
- admin-only MYH source monitoring and refresh operations.

No ORM is used.

## Backend structure

```text
backend/
  app/
    main.py                  FastAPI app assembly and router registration
    database.py              DATABASE_URL handling and psycopg connection helper
    dependencies.py          request-scoped database dependency
    exception_handlers.py    central handlers for safe API error responses
    logging_config.py        simple local logging setup
    schemas.py               response models
    queries.py               compatibility exports for older imports
    auth/
      dependencies.py        bearer-token parsing and RBAC dependencies
      models.py              safe principal and role models
      password_hashing.py    salted PBKDF2 password hashing
      repositories.py        auth user/token SQL helpers
      routes.py              /auth/login, /auth/whoami, /auth/logout
      token_store.py         retired static-token compatibility guard
      tokens.py              opaque token generation and hashing
    api_keys/
      dependencies.py        X-API-Key parsing and scope dependencies
      key_utils.py           opaque API key generation, hashing, prefixing
      models.py              API key request/response/principal models
      repositories.py        API key SQL helpers
      routes.py              /admin/api-keys management endpoints
    provider_submissions/
      dependencies.py        provider bearer identity for submissions
      models.py              provider submission request/response models
      repositories.py        provider submission SQL helpers
      routes.py              /provider/submissions CRUD endpoints
    core/
      errors.py              standard API error envelope helpers
    middleware/
      request_context.py     X-Request-ID handling
      logging_middleware.py  safe request logging
    routers/
      health.py              /, /health, /health/db
      applications.py        /applications routes
      stats.py               statistics and trend routes
      providers.py           provider browsing routes
      export.py              CSV export route
      admin.py               RBAC-protected admin-note routes
    services/
      common.py              shared filters and SQL helpers
      applications.py        application browsing and lookup queries
      stats.py               statistics and trend queries
      providers.py           provider browsing queries
      export.py              CSV export query and serializer
      health.py              database readiness checks
      database_seeder.py     safe startup schema/index bootstrap
      admin_notes.py         protected local admin-note storage
      source_check.py        legacy MYH source-page manifest helpers
    source_monitor/
      models.py              source-monitor response models
      repositories.py        source-file, check-run, refresh-run, notification SQL helpers
      routes.py              admin-only source-monitor and refresh endpoints
      scheduler.py           lightweight optional local scheduler
      service.py             parser, downloader, validator, importer, refresh orchestration
  runtime/
    README.md                explains local generated runtime files
  sql/
    reset_schema.sql         explicit full-reload reset, never used by startup
    schema.sql               safe CREATE TABLE IF NOT EXISTS schema source
    indexes.sql              safe CREATE INDEX IF NOT EXISTS indexes
    upgrade_3_16_api_keys.sql historical 3.16 upgrade reference; startup schema covers current DB
  scripts/
    load_curated_data.py
    validate_database.py
    smoke_test_api.py
    demo_api.py
    check_source_status.py
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
    test_cors.py
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

`main.py` should stay small. New endpoint work should normally go into a router, with database/query or operation logic placed in a service module. Cross-cutting behavior belongs in `auth/`, `middleware/`, `core/`, `exception_handlers.py`, and `logging_config.py`. New endpoint work should keep using routers, services, repositories, and raw SQL. Source monitoring lives in `source_monitor/` so the official historical data pipeline stays separate from provider workflow data.

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
- includes `application_notes`, `auth_users`, `auth_access_tokens`, and `api_keys` as normal project-managed tables,
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

By default, the loader runs `reset_schema.sql`, then the safe `schema.sql`, then `indexes.sql`. This keeps destructive full reload behavior explicit and separate from API startup. The loader reloads lookup rows and application rows from the curated CSV. In 3.20, `POST /refresh` is admin-only and routes through the robust refresh service; compatibility refresh can still reload the curated CSV, while selected official source files can be downloaded, validated, and imported by affected source years. `application_notes`, `auth_users`, `auth_access_tokens`, `api_keys`, provider submissions, review events, MYH source records, refresh runs, and admin notifications are not reset by curated-data reloads.

## Validate the database

```bash
python backend/scripts/validate_database.py --csv-path ../path/to/myh_curated_applications_2020_2025.csv
```

The validator checks row count, unique `diarienummer`, year coverage, normalized decisions, record preservation, and lookup-table foreign-key consistency.

## MYH source monitoring and refresh operations

Sub-project 3.20 upgrades source checking into a database-backed, admin-only operations layer. It does not require live MYH access in tests; parser, route, download, validation, import, and scheduler behavior are covered with mocked HTML/files/network responses.

The source-monitoring service can:

- fetch the official MYH source page configured by environment,
- parse official downloadable Excel/CSV result files and ignore PDFs/unrelated links,
- record source files, source check runs, refresh runs, and admin notifications in PostgreSQL,
- create unread notifications for new/changed source files and refresh success/failure,
- download selected source files under `backend/runtime/source_files/`,
- compute SHA256 for downloaded files,
- transform Tabell 3-style official files into the applications import shape,
- validate required columns, decisions, years, duplicates, and row counts,
- import atomically by replacing/upserting only affected official `source_year` values,
- leave users, sessions, API keys, provider submissions, review events, and notifications untouched.

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

The scheduler is disabled by default and should stay disabled in tests. Scheduled checks detect and notify only unless `PART3_REFRESH_AUTO_IMPORT=true` is explicitly set.

Admin-only endpoints:

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

`POST /refresh` remains as a compatibility endpoint, but it requires an admin bearer session. Public callers, providers, and export-only API keys cannot trigger source checks, downloads, imports, or refresh.

Generated runtime files are local machine state and should not be committed:

```text
backend/runtime/source_files/
backend/runtime/processed/
backend/runtime/*.xlsx
backend/runtime/*.xls
backend/runtime/*.csv
backend/runtime/*.parquet
```

## Run focused tests

The pytest layer is intentionally small. It does not require a live PostgreSQL database, and the source-check tests use mocked HTTP responses instead of live internet.

From `part_3`:

```bash
python -m compileall backend/app backend/scripts
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
- request-id and request-logging middleware,
- standardized safe error envelopes,
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
http://127.0.0.1:8000/admin/source-monitor/status
http://127.0.0.1:8000/docs
```

`/docs` opens the automatic Swagger/OpenAPI documentation generated by FastAPI.


## Request IDs, request logging, and API errors

Sub-project 3.14 adds a cross-cutting middleware/error foundation for the backend. Sub-project 3.15 uses that foundation for centralized token authentication and role-based authorization. API keys, provider submission CRUD, and admin review workflow are now implemented. Authenticated React workspaces remain planned later.

### Request IDs

Every HTTP response includes `X-Request-ID`.

Behavior:

- if the caller sends a safe `X-Request-ID`, the backend echoes it,
- if the header is missing or unsafe, the backend generates a UUID,
- the request id is stored on `request.state.request_id`,
- request logs and error responses include the same id.

Example:

```bash
curl -i -H "X-Request-ID: demo-request-123" "http://127.0.0.1:8000/health"
```

### Safe request logging

The request logger writes one concise line per request with:

```text
request_id method path safe query string status_code duration_ms client_host
```

It does not log admin tokens, authorization headers, API keys, request bodies, or response bodies. Token-like query values such as `api_key`, `token`, `password`, or `secret` are redacted before logging.

### Safe error response shape

Expected HTTP errors, validation errors, PostgreSQL errors, and unexpected exceptions are handled centrally. Responses use this shape:

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

The `error` object is the stable new response envelope. The top-level `detail` field remains for compatibility with existing FastAPI/browser helpers. Important status codes are preserved, including 400, 401, 403, 404, 422, 500, and 503. Unexpected exceptions return a generic safe message instead of stack traces or internal details.

Useful manual checks:

```bash
curl -i "http://127.0.0.1:8000/does-not-exist"
curl -i "http://127.0.0.1:8000/applications?limit=wrong"
```

## Local dashboard CORS

Sub-project 3.13 adds narrow CORS middleware for local React/Vite development only.

Allowed origins:

```text
http://localhost:5173
http://127.0.0.1:5173
```

Allowed methods are limited to `GET` and `OPTIONS`, which is enough for the public dashboard endpoints. This does not expose admin tokens and does not make protected `/admin` behavior public.

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

## Health and operations endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Lightweight process check. It confirms that FastAPI can respond. |
| `GET /health/db` | Database readiness check. It confirms connection, required tables, application rows, and lookup rows. |
| `GET /admin/source-monitor/status` | Admin-only status for monitor configuration, last check, latest refresh, and unread notifications. |
| `POST /admin/source-monitor/check` | Admin-only live source-page check that records new/changed/known files and creates notifications. |

Use `/health` for quick “is the API process alive?” checks. Use `/health/db` before demonstrations or frontend work that depends on actual loaded data. Use `/admin/source-monitor/status` and `/admin/source-monitor/check` when demonstrating operational refresh governance.

## Endpoint overview

### Service and operational endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /` | Small service landing response for browser checks. |
| `GET /health` | Confirms that the API process is running. |
| `GET /health/db` | Confirms database readiness for real API use. |
| `GET /admin/source-monitor/status` | Shows admin-only monitor status, last check, latest refresh, and unread notifications. |
| `POST /admin/source-monitor/check` | Checks the official MYH source page and records new/changed/known downloadable source files. |
| `GET /admin/source-files` | Lists detected official MYH source files. |
| `POST /admin/source-files/{source_file_id}/download` | Downloads one source file to runtime storage and records SHA256. |
| `POST /admin/source-files/{source_file_id}/import` | Validates and atomically imports one official source file by affected source year. |
| `GET /admin/refresh-runs` | Lists validation/import/compatibility refresh runs. |
| `GET /admin/notifications` | Lists admin operational notifications. |
| `POST /admin/notifications/{notification_id}/read` | Marks one notification as read. |
| `POST /admin/notifications/{notification_id}/resolve` | Resolves one notification. |
| `POST /refresh` | Admin-only compatibility refresh routed through the robust refresh service. |
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
| `GET /export/applications` | Returns a downloadable filtered CSV export when `X-API-Key` has `export:read`. |

## Authentication and role-based authorization

Sub-project 3.15.1 upgrades the centralized RBAC foundation into database-backed authentication. The backend stores users in PostgreSQL, stores only salted PBKDF2-HMAC-SHA256 password hashes, issues opaque bearer access tokens from `/auth/login`, stores only token hashes, and supports token expiry and logout/revocation.

Auth tables:

```text
auth_users
auth_access_tokens
```

Bootstrap environment variables create local users safely during startup. They are not request-time credentials:

```text
PART3_BOOTSTRAP_ADMIN_USERNAME=admin
PART3_BOOTSTRAP_ADMIN_PASSWORD=admin-password
PART3_BOOTSTRAP_ADMIN_DISPLAY_NAME=Local Admin

PART3_BOOTSTRAP_PROVIDER_USERNAME=provider
PART3_BOOTSTRAP_PROVIDER_PASSWORD=provider-password
PART3_BOOTSTRAP_PROVIDER_DISPLAY_NAME=Local Provider
PART3_BOOTSTRAP_PROVIDER_ID=999999
```

Bootstrap is idempotent. Existing users are left unchanged, including their passwords. The backend can start without these variables, but login only works when matching users already exist in `auth_users`. Raw passwords, raw access tokens, password hashes, and token hashes must not be logged.

Standard request format after login:

```text
Authorization: Bearer <database-issued-access-token>
```

Roles:

```text
admin
provider
```

Endpoints:

```text
POST /auth/login
GET  /auth/whoami
POST /auth/logout
```

A successful login returns the raw token once:

```json
{
  "access_token": "returned-once",
  "token_type": "bearer",
  "expires_at": "2026-05-29T..."
}
```

`GET /auth/whoami` returns only safe principal fields. Admin example:

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

Auth failures use the standardized error envelope from the 3.14 error system. Missing, malformed, invalid, expired, or revoked bearer tokens return 401. Valid credentials with the wrong role return 403. All responses still include `X-Request-ID`; error bodies include the same request ID.

This is a real internal database-backed auth system for the project, not OAuth, SSO, MFA, JWT, or enterprise IAM. API keys are implemented separately in 3.16 for machine/client access. Provider submission CRUD is implemented in 3.17 and admin review/decision workflow is implemented in 3.18. Authenticated React admin/provider pages are later roadmap steps.

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

Sub-project 3.12 adds a small local write-side feature under `/admin`. Sub-project 3.15.1 protects those routes with database-backed admin bearer tokens. Public read endpoints remain public.

Admin requests use:

```text
Authorization: Bearer <database-issued-admin-access-token>
```

The previous static local admin header is no longer accepted for request-time access.

Example flow:

```bash
curl -X POST "http://127.0.0.1:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin-password"}'

curl -H "Authorization: Bearer <admin-access-token>" \
  "http://127.0.0.1:8000/auth/whoami"

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

## Common example requests

### Source status and source check

```bash
curl "http://127.0.0.1:8000/admin/source-monitor/status"
curl -X POST "http://127.0.0.1:8000/admin/source-monitor/check"
```

`GET /admin/source-monitor/status` is safe to call frequently because it only reads the local manifest. `POST /admin/source-monitor/check` performs a live page check and updates the manifest, but does not modify application data.

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
curl -OJ -H "X-API-Key: <export-api-key>" "http://127.0.0.1:8000/export/applications?year=2024&decision=approved"
curl -OJ -H "X-API-Key: <export-api-key>" "http://127.0.0.1:8000/export/applications?provider=KYH"
curl -OJ -H "X-API-Key: <export-api-key>" "http://127.0.0.1:8000/export/applications?provider_id=1"
curl -OJ -H "X-API-Key: <export-api-key>" "http://127.0.0.1:8000/export/applications?year=2025&region=Stockholm&limit=100"
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

`year` is the preferred user-facing filter and maps to the database field `source_year`. `source_year` is also accepted as an alias. If both are used, they must have the same value. Missing, invalid, expired, or revoked API keys return 401; a valid key without `export:read` returns 403.

### Operational refresh

3.20 keeps `POST /refresh` for compatibility, but it is no longer a public/toy endpoint. It requires an admin bearer session and calls the same refresh orchestration used by the source-monitoring feature.

Typical admin flow:

```bash
# Login first and copy the returned access_token.
curl -X POST "http://127.0.0.1:8000/auth/login" ^
  -H "Content-Type: application/json" ^
  -d "{"username":"admin","password":"admin-password"}"

# Check the official source page.
curl -X POST "http://127.0.0.1:8000/admin/source-monitor/check" ^
  -H "Authorization: Bearer <admin-token>"

# Download/import a selected detected source file.
curl -X POST "http://127.0.0.1:8000/admin/source-files/<source_file_id>/download" ^
  -H "Authorization: Bearer <admin-token>"

curl -X POST "http://127.0.0.1:8000/admin/source-files/<source_file_id>/import" ^
  -H "Authorization: Bearer <admin-token>"
```

Compatibility refresh from the existing curated CSV is still available for local demos:

```bash
curl -X POST "http://127.0.0.1:8000/refresh" ^
  -H "Authorization: Bearer <admin-token>"
```

Current refresh/import behavior:

- validates required fields before import,
- computes and stores source-file SHA256 when downloading,
- records refresh runs with status, row count, affected years, validation summary, and request ID/error details,
- uses database transactions and rolls back failed imports,
- replaces only affected official `source_year` values for official source imports,
- does not reset users, sessions, API keys, provider submissions, review events, admin notifications, or source-monitor history.

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

The smoke test checks the root endpoint, `/health`, `/health/db`, `/admin/source-monitor/status`, refresh, core browsing/statistics/provider/export endpoints, and important guardrails. Admin-note and API-key management endpoints are shown in the demo helper and covered by focused route tests. Runtime API-key flows should be tested manually with a database-issued admin bearer token from `/auth/login`.

## 3.18 scope boundary

Implemented by the end of 3.18:

- MYH source-check service and operation endpoints,
- protected admin application notes under `/admin`,
- database-backed `auth_users` and `auth_access_tokens`,
- salted PBKDF2 password hashes and opaque bearer access tokens,
- `/auth/login`, `/auth/whoami`, and `/auth/logout`,
- admin/provider bearer-session role checks,
- safe startup database seeder through `schema.sql`, code-managed review upgrade logic, and `indexes.sql`,
- React + TypeScript public dashboard in `part_3/frontend`,
- local-development CORS for the Vite dashboard,
- request ID handling with `X-Request-ID`, safe request logging, and standardized error response envelopes,
- database-backed `api_keys` table,
- hashed API key storage with raw key returned once,
- admin-only API key create/list/revoke endpoints,
- `X-API-Key` machine authentication separate from bearer user sessions,
- `export:read` scope requirement on `GET /export/applications`,
- public read/statistics/provider endpoints preserved without API keys,
- provider-authenticated submission CRUD under `/provider/submissions`,
- `provider_application_submissions` with statuses `draft`, `submitted`, `under_review`, `needs_changes`, `approved`, and `rejected`,
- `provider_submission_review_events` for review/status-transition history,
- admin-authenticated review endpoints under `/admin/provider-submissions`,
- provider update/resubmission after `needs_changes`,
- code-managed non-destructive upgrade of existing 3.17 databases,
- focused schema, repository, route, auth-boundary, request-ID, and regression tests.

Still not implemented after 3.18:

- authenticated React admin/provider workspace,
- ML extension,
- automatic source-file download and curated CSV replacement,
- production scheduler or background worker,
- ORM conversion.

## Sub-project 3.19 authenticated workspace backend

3.19 keeps the existing 3.15.1 database-backed authentication model. It does not add JWT, OAuth, `X-Admin-Token`, frontend-only fake roles, or API-key login.

### Controlled provider signup

Public provider signup is a request workflow, not instant self-registration:

```text
POST /auth/registration-requests
```

The request captures requested username, display name, password hash, provider ownership, optional email/organization/message, and status. New requests start as `pending`. They do not create an active `auth_users` row until an admin approves them.

Admin review endpoints:

```text
GET  /admin/registration-requests
GET  /admin/registration-requests/{request_id}
POST /admin/registration-requests/{request_id}/approve
POST /admin/registration-requests/{request_id}/reject
```

Approval creates an active provider user with the existing password hashing/session login system. Rejection preserves the request for history and does not create a user.

### Admin user management

Admin-only user-management endpoints:

```text
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

Admins can create admin/provider users, update safe profile fields, reset passwords, deactivate/reactivate users, inspect safe session metadata, and revoke sessions. Provider users require a provider ownership value. User-management responses never expose passwords, password hashes, token hashes, API key values, or API key hashes.

### Code-managed database objects

The 3.19 objects are included in the normal safe startup schema/index path:

```text
user_registration_requests
auth_admin_events
```

Relevant indexes are also managed by `backend/sql/indexes.sql` and registered in `database_seeder.py`. The user should not run manual `CREATE TABLE`, `ALTER TABLE`, or `CREATE INDEX` statements for 3.19.

### Frontend CORS

Local Vite development is allowed by environment-aware CORS settings. The default local origins remain:

```text
http://localhost:5173
http://127.0.0.1:5173
```

The method list includes the write methods needed by the authenticated React workspace.

### Demo flow helper

`backend/scripts/demo_api.py --print-only` now lists the controlled signup, admin registration-review, admin user-management, provider submission, admin review, public data, and API-key export boundaries in one presentation-friendly flow.
