# GitHub Copilot Instructions for DB2API-Exposure

## Scope
These instructions apply repository-wide. Prefer local instructions under `.github/instructions/*.instructions.md` when editing specific areas.

## Directory Boundaries
- Edit backend logic only in `backend/`.
- Edit UI only in `frontend/`.
- Edit container/runtime setup only in `docker/` and `docker-compose.yml`.
- Update docs in `docs/` when behavior changes.

## Required Architecture Rules
- Use Python 3.12+ for backend code.
- Use FastAPI with versioned routes.
- Admin routes: `/api/v1/admin/*`.
- Data routes: `/api/v1/data/*`.
- Use Pydantic Settings v2 for config.
- Use SQLAlchemy 2.0 + Alembic for app DB schema.
- Use PyJWT + bcrypt for auth.
- Use structlog structured logging.
- Use Vite + React SPA for frontend.
- Include rich SQL editor in wizard flows (Monaco or CodeMirror 6).

## Build and Test Commands
- Backend setup: `cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`.
- Backend run: `cd backend && uvicorn app.main:app --reload`.
- Backend checks: `cd backend && ruff check . && mypy . && pytest`.
- Frontend setup: `cd frontend && npm install`.
- Frontend run: `cd frontend && npm run dev`.
- Frontend checks: `cd frontend && npm run eslint && npm run prettier:check && npm run test`.
- Docker checks: `docker compose build` and `docker compose up -d`.

## Mandatory Safety Rules
- SQL must be parameterized with bind params only (`:param_name`).
- Never generate SQL using string concatenation from user input.
- Never store secrets in code, tests, fixtures, or docs.
- Never break existing `/api/v1/*` contracts without version bump + migration notes.
- Never change an applied Alembic revision; add a new revision.

## Review Expectations for Suggested Changes
- Include tests with behavior changes.
- Include migration for schema changes.
- Include docs updates for API/config/workflow changes.
- Keep changes minimal and scoped to request.
- Explain risks when touching auth, SQL execution, migrations, or scheduler logic.

## Stop Conditions
- If API contract is unclear, inspect existing `/api/v1` routers and docs.
- If schema intent is unclear, inspect current models + Alembic history.
- If ambiguity remains, ask for clarification instead of inventing endpoints or fields.
