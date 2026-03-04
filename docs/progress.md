# Implementation Progress

## Phase 0: Repository Scaffolding, CI/CD, Docker, Conventions — COMPLETE

**Completed:** 2026-03-04

### Delivered
- Monorepo directory skeleton: `backend/`, `frontend/`, `docker/`, `docs/`
- Backend: FastAPI skeleton, Pydantic Settings v2, `requirements.txt`, `pyproject.toml` (ruff/mypy/pytest)
- Frontend: Vite 6 + React 18 + TypeScript, Tailwind CSS, shadcn/ui CSS vars, ESLint, Prettier, Vitest; `vite.config.ts` (ESM-safe, `import.meta.url`), `vitest.config.ts` (separate to avoid vitest/vite type conflict)
- Docker: `Dockerfile.backend` (python:3.12-slim + curl), `Dockerfile.frontend` (multi-stage + nginx), `docker-compose.yml` (`api`/`web`/`db` + optional `oracle` profile)
- GitHub Actions: `backend.yml` (ruff/mypy/pytest + Postgres service), `frontend.yml` (eslint/prettier/vitest/build), `docker.yml` (image builds + compose config validate)
- Docs: `docs/architecture.md`, `docs/contributing.md`, `docs/conventions.md`, root `Makefile`, `.env.example`, `.gitignore`

### Bug Fixes Applied
- `vite.config.ts`: replaced `__dirname` (undefined in ESM) with `fileURLToPath(new URL(..., import.meta.url))`
- `tsconfig.app.json` / `tsconfig.node.json`: added `"composite": true` for `tsc -b` project reference builds
- `tsconfig.node.json`: added `"types": ["node"]` for Node.js built-in module resolution in config files
- `tsconfig.app.json`: added `"types": ["vitest/globals"]` for test globals without explicit imports
- `vitest.config.ts`: extracted test config from `vite.config.ts` (using `mergeConfig`) to avoid vitest-bundled-vite plugin type conflict
- `Dockerfile.backend`: added `curl` to apt install (required by `docker-compose.yml` healthcheck)
- `requirements.txt`: removed duplicate `httpx` entry and unused `types-passlib`
- `frontend/package-lock.json`: committed so `npm ci` succeeds in CI

---

## Phase 1: Backend Foundation — IN PROGRESS

**Started:** 2026-03-04

### Goals
Deliver the core FastAPI service skeleton with configuration, persistence, observability, and migration baseline.

### Deliverables
- [x] App factory with startup lifecycle, middleware pipeline, exception handlers
- [x] Structured logging (structlog) with request correlation IDs
- [x] SQLAlchemy 2.0 async models: 8 domain tables
- [x] Alembic async migration environment + initial schema migration
- [x] PostgreSQL async database layer (asyncpg)
- [x] Health endpoints: `/api/v1/admin/health/live` and `/api/v1/admin/health/ready`
- [x] Repository/service layer boundary patterns
- [x] Full test suite update with pytest-asyncio + httpx.AsyncClient

### Domain Tables Modelled
| Table | Model | Purpose |
|-------|-------|---------|
| `connections` | `OracleConnection` | Oracle data source configs |
| `auth_methods` | `AuthMethod` | Bearer / Basic / API-key auth configs |
| `endpoints` | `ApiEndpoint` | Dynamic REST endpoint definitions |
| `schedules` | `Schedule` | Cron/interval snapshot refresh schedules |
| `job_runs` | `JobRun` | Scheduler execution audit records |
| `snapshots` | `Snapshot` | Cached JSONB query results |
| `access_logs` | `AccessLog` | Per-request access audit trail |
| `app_settings` | `AppSetting` | Key-value application settings |

---

## Phase 2: Module 1 - Connections End-to-End — PENDING

## Phase 3: Module 3 - Auth Configuration End-to-End — PENDING

## Phase 4: Module 2 - API Creation Wizard End-to-End — PENDING

## Phase 5: Module 4 - Scheduling + Snapshot Cache End-to-End — PENDING

## Phase 6: Module 5 - Settings + Health Dashboard End-to-End — PENDING

## Phase 7: Integration Hardening — PENDING
