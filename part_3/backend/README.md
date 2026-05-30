# Part 3 Backend — PostgreSQL and FastAPI

This folder contains the Part 3 backend for storing and exposing the curated MYH applications dataset.

Sub-projects 3.2-3.8 built the working backend gradually: PostgreSQL storage, core read API, richer statistics, provider browsing, filtered CSV export, trend statistics, operational refresh, and final validation/demo readiness.

Sub-project 3.10 reorganized that backend into a clearer structure and added database readiness checks, simple logging, centralized database-error handling, and focused pytest coverage.

Sub-project 3.11 added a scheduler-ready MYH source-check foundation, local source-status manifest, source-check operation endpoints, refresh metadata, a manual source-check script, and focused tests that do not depend on live internet access. Sub-project 3.12 adds protected admin application notes as a small safe write-side use case. Sub-project 3.12.1 adds safe database seeder/startup initialization with SQL files as the single schema source of truth. Sub-project 3.13 adds minimal local-development CORS support so the React/Vite dashboard can call the public API from the browser. Sub-project 3.14 adds request IDs, safe request logging, and standardized API error envelopes. Sub-project 3.15 adds centralized RBAC foundations. Sub-project 3.15.1 upgrades authentication to PostgreSQL-backed users, hashed passwords, issued opaque bearer tokens, logout/revocation, and database-backed role authorization. Sub-project 3.16 adds database-backed API keys for machine/client access, admin-only API-key management, scoped `X-API-Key` dependencies, and API-key protection for CSV exports.

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
- database-backed API keys for scoped machine/client export access.

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
      operations.py          refresh and source-check operation routes
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
      source_check.py        MYH source-page check and manifest helpers
  runtime/
    README.md                explains local generated runtime files
  sql/
    reset_schema.sql         explicit full-reload reset, never used by startup
    schema.sql               safe CREATE TABLE IF NOT EXISTS schema source
    indexes.sql              safe CREATE INDEX IF NOT EXISTS indexes
    upgrade_3_16_api_keys.sql optional manual non-destructive API-key upgrade
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
    test_routes.py
    test_schemas_and_export.py
    test_source_check_service.py
```

`main.py` should stay small. New endpoint work should normally go into a router, with database/query or operation logic placed in a service module. Cross-cutting behavior belongs in `auth/`, `middleware/`, `core/`, `exception_handlers.py`, and `logging_config.py`. The next implementation layer is provider application submission CRUD, not another auth rewrite.

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

By default, the loader runs `reset_schema.sql`, then the safe `schema.sql`, then `indexes.sql`. This keeps destructive full reload behavior explicit and separate from API startup. The loader reloads lookup rows and application rows from the curated CSV. The API refresh endpoint uses the same loading helper. `application_notes`, `auth_users`, `auth_access_tokens`, and `api_keys` are not reset by the curated-data reload.

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
http://127.0.0.1:8000/operations/source-status
http://127.0.0.1:8000/docs
```

`/docs` opens the automatic Swagger/OpenAPI documentation generated by FastAPI.


## Request IDs, request logging, and API errors

Sub-project 3.14 adds a cross-cutting middleware/error foundation for the backend. Sub-project 3.15 uses that foundation for centralized token authentication and role-based authorization. API keys, provider CRUD, admin review workflow, and authenticated React workspaces remain planned later.

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

This is a real internal database-backed auth system for the project, not OAuth, SSO, MFA, JWT, or enterprise IAM. API keys are implemented separately in 3.16 for machine/client access. Provider CRUD, admin review/decision workflow, and authenticated React admin/provider pages are later roadmap steps.

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
- preserves local `application_notes`, `auth_users`, `auth_access_tokens`, and `api_keys` rows.

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

The smoke test checks the root endpoint, `/health`, `/health/db`, `/operations/source-status`, refresh, core browsing/statistics/provider/export endpoints, and important guardrails. Admin-note and API-key management endpoints are shown in the demo helper and covered by focused route tests. Runtime API-key flows should be tested manually with a database-issued admin bearer token from `/auth/login`.

## 3.16 scope boundary

Implemented by the end of 3.16:

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
- database-backed auth users with salted PBKDF2 password hashes,
- opaque bearer access tokens with hashed storage, expiry, and logout/revocation,
- `/auth/login`, `/auth/whoami`, and `/auth/logout`,
- admin-note protection through database-issued admin bearer tokens,
- provider bearer tokens rejected from admin routes with 403,
- safe startup database seeder through `schema.sql` and `indexes.sql`,
- React + TypeScript dashboard in `part_3/frontend`,
- local-development CORS for the Vite dashboard,
- request ID handling with `X-Request-ID`,
- safe request logging middleware,
- standardized safe error response envelopes,
- focused middleware and error-handler tests,
- database-backed `api_keys` table,
- hashed API key storage with raw key returned once,
- admin-only API key create/list/revoke endpoints,
- `X-API-Key` machine authentication separate from bearer user sessions,
- `export:read` scope requirement on `GET /export/applications`,
- public read/statistics/provider endpoints preserved without API keys,
- API-key utility, repository, dependency, route, export-protection, and regression tests.

Still not implemented after 3.16:

- provider-submitted application CRUD,
- admin review/decision workflow,
- authenticated React admin/provider workspace,
- ML extension,
- automatic source-file download and curated CSV replacement,
- production scheduler or background worker,
- ORM conversion.
