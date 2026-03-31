# QueryGateway Agent Guide (Canonical)

## Mission
Build and maintain a secure, testable monorepo for dynamic SQL-to-API exposure with:
- Backend: Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic, APScheduler 3.x, Pydantic Settings v2, PyJWT, bcrypt, structlog.
- Frontend: Vite + React SPA, TypeScript, shadcn/ui, Tailwind.
- Infra: Docker + docker-compose, GitHub Actions CI.

## Repo Map and Boundaries
- `backend/` owns API contracts, DB schema, migrations, auth, scheduler, SQL execution safety.
- `frontend/` owns admin UI only (wizard, connections, auth config, schedules, settings, health dashboard).
- `docker/` owns images, compose support assets, runtime container config.
- `docs/` owns architecture notes, API version/deprecation notes, runbooks.
- Do not move logic across boundaries without updating docs and tests.

## Non-Negotiable Rules
- API versioning is required from day one.
- Admin routes must be under `/api/v1/admin/*`.
- Data routes must be under `/api/v1/data/*`.
- All data endpoints require authentication.
- All user SQL must use bind parameters only.
- Never string-concatenate SQL.
- Alembic migration is required for every schema change.
- Never edit an already-applied migration; create a new revision.
- Password hashing must use `bcrypt`.
- JWT must use `PyJWT` and include expiration (`exp`).
- Logging must be structured via `structlog`.

## SQL Safety Contract
- Allowed bind style: `:param_name`.
- Parameter mapping source: validated request inputs -> typed schema -> bind dict.
- Reject queries containing interpolated values from raw strings.
- Execute user SQL through SQLAlchemy Core `text()` with bound params.

## Required Log Fields
- `request_id`
- `user`
- `endpoint`
- `status`
- `duration_ms`
- `method`
- `client_ip`
- `event`

## Before Editing (Agent Procedure)
- Scan relevant files first.
- State intended change scope.
- List commands you will run before making edits.
- Confirm whether DB schema or API contract is affected.

## After Editing (Agent Procedure)
- Run formatting/lint/tests for changed areas.
- Add/update Alembic migration when schema changed.
- Update docs when contracts, settings, or workflows changed.
- Verify no secrets/tokens/credentials are committed.

## Stop Conditions
- If schema behavior is unclear, inspect Alembic history before coding.
- If API behavior is unclear, check `/api/v1` contract and existing routers.
- If request is ambiguous, do not invent endpoints or fields.

## Definition of Done
- Relevant tests pass locally.
- CI-equivalent checks pass for changed scope.
- Migrations included when needed.
- Versioning/deprecation policy respected.
- No security rule violations.
