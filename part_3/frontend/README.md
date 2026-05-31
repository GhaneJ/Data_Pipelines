# Part 3 Frontend — Authenticated React Workspace

This folder contains the React + TypeScript browser workspace for Part 3.

Sub-project 3.19 extends the previous public dashboard into a real authenticated portal that uses the backend 3.15.1 database-issued bearer sessions, the 3.16 API-key boundary, the 3.17 provider submission API, and the 3.18 admin review workflow.

## Stack

```text
Vite
React
TypeScript
Recharts
plain CSS
Vitest + Testing Library
```

The app does not use JWT, OAuth, fake frontend users, `X-Admin-Token`, or API keys for human login.

## Backend requirement

Start the backend first from `part_3`:

```bash
python -m uvicorn backend.app.main:app --reload
```

Make sure `DATABASE_URL` points to the local PostgreSQL database before starting the backend.

PowerShell example:

```powershell
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/myh_applications"
```

## Frontend configuration

The default backend URL is:

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

## Routes

```text
/login
/signup
/admin
/admin/users
/admin/signup-requests
/admin/provider-submissions
/admin/api-access
/provider
/provider/submissions
/data
/data/applications
/data/stats
```

Root `/` redirects according to the current authenticated role, or to `/login` when no human session exists.

## Authentication behavior

The login page calls:

```text
POST /auth/login
GET  /auth/whoami
POST /auth/logout
```

The bearer token is stored in `sessionStorage`, not `localStorage`. The shared API client attaches:

```text
Authorization: Bearer <database-issued-session-token>
```

when a user session exists. It clears the session on `401` and surfaces backend request IDs on errors.

The React workspace never sends `X-API-Key` for human login, admin screens, provider screens, or route guarding.

## Controlled signup flow

The public signup/request-access page calls:

```text
POST /auth/registration-requests
```

This creates a pending provider access request only. It does not create an active login session and it does not allow public admin signup.

Admin users review those requests through:

```text
/admin/signup-requests
```

Approval creates the real active provider user. Rejection preserves the request history without creating a user.

## Admin workspace

Admin users can:

- view summary cards for users, pending signup requests, and provider review work,
- manage users,
- create admin/provider users,
- update safe user metadata,
- deactivate/reactivate users,
- reset passwords,
- inspect/revoke sessions,
- review provider access requests,
- inspect the API-key boundary,
- review provider submissions and workflow events.

Passwords, bearer tokens, token hashes, API key values, and API key hashes are never displayed.

## Provider workspace

Provider users can:

- view only their own provider submissions,
- create drafts,
- edit drafts,
- submit drafts for admin review,
- see status badges,
- see admin feedback on `needs_changes`,
- edit and resubmit `needs_changes`,
- see final approved/rejected states.

The frontend hides blocked actions by workflow state, while the backend remains the authority for authorization and workflow transitions.

## Public/shared data explorer

The `/data` area keeps the original dashboard behavior and consumes public backend endpoints such as:

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

Public MYH historical data remains separate from provider-created workflow submissions.

## API-key boundary

The admin API access page explains the machine-access boundary. API keys remain for scoped machine clients, especially:

```text
GET /export/applications
X-API-Key: <database-issued-api-key with export:read>
```

API keys do not grant React login, admin workspace access, provider workspace access, signup approval, or provider submission review.

## Validation

From `part_3/frontend`:

```bash
npm install
npm run lint
npm test -- --run
npm run build
```

`npm run lint` is intentionally lightweight: it runs TypeScript type-checking with `tsc --noEmit`.

## Files not to commit

Do not commit generated frontend files such as:

```text
node_modules/
dist/
.vite/
coverage/
tsconfig.tsbuildinfo
tsconfig.node.tsbuildinfo
```
