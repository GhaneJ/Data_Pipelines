# Part 3 Frontend — React + TypeScript Dashboard

This folder contains the Sub-project 3.13 dashboard for the MYH applications data service.

The dashboard is intentionally presentation-friendly and vocational/YH-student explainable. It is not a separate production product. It consumes the existing FastAPI backend and helps demonstrate that the curated dataset can be used by another part of a system.

## Stack

```text
Vite
React
TypeScript
Recharts
plain CSS
Vitest + Testing Library
```

No admin token is stored in frontend code. Protected admin-note endpoints are not exposed in the public dashboard.

## Backend requirement

Start the backend first from `part_3` and make sure `DATABASE_URL` points to the existing local PostgreSQL database:

```bash
python -m uvicorn backend.app.main:app --reload
```

Useful backend checks:

```text
http://127.0.0.1:8000/health/db
http://127.0.0.1:8000/docs
```

## Frontend configuration

The default API base URL is:

```text
http://127.0.0.1:8000
```

Override it with `VITE_API_BASE_URL` when needed.

PowerShell:

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm run dev
```

macOS/Linux:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

## Install and run

From `part_3/frontend`:

```bash
npm install
npm run dev
```

Open the Vite URL, normally:

```text
http://localhost:5173
```

## Dashboard features

The dashboard includes:

- API reachability and database-readiness status,
- summary cards for total applications, decisions, year range, and approval-rate movement,
- applications-by-year chart,
- decision trend chart,
- region and education-area charts,
- bounded filterable application browser,
- selected application detail panel,
- loading, empty, and error states for safer demos.

## Public API endpoints consumed

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

The public dashboard does not call:

```text
/admin/...
POST /refresh
POST /operations/check-source
```

Those backend features should be validated separately from the API/docs/tests when needed.

## Validation

From `part_3/frontend`:

```bash
npm install
npm run build
npm run lint
npm test
```

`npm run lint` is intentionally lightweight: it runs TypeScript type-checking with `tsc --noEmit`.

## Files not to commit

Do not commit generated frontend files such as:

```text
node_modules/
dist/
.vite/
coverage/
```
