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

## Phase 1: Backend Foundation — COMPLETE

**Completed:** 2026-03-04

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

---

## Phase 2: Module 1 - Connections End-to-End — COMPLETE

**Completed:** 2026-03-04

### Goals
Provide complete connection lifecycle management for Oracle data sources.

### Delivered

#### Backend
| File | Purpose |
|------|---------|
| `backend/app/crypto.py` | Fernet symmetric encryption for credentials at rest |
| `backend/app/config.py` | Added `encryption_key` setting (Fernet key) |
| `backend/app/schemas/connection.py` | `ConnectionCreate` / `ConnectionUpdate` / `ConnectionResponse` / `ConnectionTestResult` |
| `backend/app/repositories/connection.py` | Async SQLAlchemy repository (get, list, create, update, delete) |
| `backend/app/services/connection.py` | Business logic: encrypt/decrypt, uniqueness guard, Oracle connectivity test, audit logging |
| `backend/app/routers/connections.py` | REST CRUD + `/test` under `/api/v1/admin/connections/*` |
| `backend/tests/test_connections.py` | Crypto unit tests + schema validation tests + API integration tests |

#### API Surface
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/admin/connections/` | List connections (`?active_only=true`) |
| POST | `/api/v1/admin/connections/` | Create connection (201) |
| GET | `/api/v1/admin/connections/{id}` | Get single connection |
| PUT | `/api/v1/admin/connections/{id}` | Update connection |
| DELETE | `/api/v1/admin/connections/{id}` | Delete connection (204) |
| POST | `/api/v1/admin/connections/{id}/test` | Test Oracle connectivity |

#### Security
- Passwords encrypted with Fernet (AES-128-CBC + HMAC-SHA256) before persistence
- `encrypted_password` never returned in any API response
- `has_password: bool` field indicates credentials are stored
- Audit log entries on create / update / delete / test actions

#### Frontend
| File | Purpose |
|------|---------|
| `frontend/src/types/connection.ts` | TypeScript interfaces matching API contract |
| `frontend/src/lib/api.ts` | Axios-based API client (`connectionsApi`) |
| `frontend/src/lib/queryClient.ts` | React Query `QueryClient` + key factories |
| `frontend/src/lib/utils.ts` | `cn()` Tailwind merge utility |
| `frontend/src/components/ui/` | Button, Input, Label, Badge, Select, Textarea, Dialog, Alert |
| `frontend/src/components/Layout.tsx` | Sidebar + `<Outlet>` shell with nav links |
| `frontend/src/components/connections/ConnectionForm.tsx` | Create/edit form with client-side validation |
| `frontend/src/pages/ConnectionsPage.tsx` | List table + create/edit/delete/test dialogs |
| `frontend/src/pages/DashboardPage.tsx` | Overview dashboard with connection count card |
| `frontend/src/App.tsx` | React Router + QueryClientProvider wiring |

#### Checks
- `ruff check .` — clean
- `mypy .` — clean (alembic/ excluded from strict)
- `pytest -k "not integration"` — 22 passed
- `eslint` — clean
- `prettier --check` — clean
- `tsc -b && vite build` — clean

---

## Phase 3: Module 3 - Auth Configuration End-to-End — COMPLETE

**Completed:** 2026-03-05

### Goals
Deliver configurable endpoint authentication using PyJWT + bcrypt.

### Delivered

#### Backend
| File | Purpose |
|------|---------|
| `backend/app/auth/jwt_utils.py` | JWT creation/verification (PyJWT, HS256/384/512) |
| `backend/app/auth/hashing.py` | bcrypt password hashing, API key generation, signing secret generation |
| `backend/app/models/auth_method.py` | `AuthMethod` model with `AuthMethodType` enum (bearer/basic/api_key) |
| `backend/app/models/access_log.py` | `AccessLog` model for per-request access audit trail |
| `backend/app/schemas/auth_method.py` | `AuthMethodCreate` / `AuthMethodUpdate` / `AuthMethodResponse` / `TokenIssuedResponse` / `ApiKeyIssuedResponse` / `RotateResponse` |
| `backend/app/repositories/auth_method.py` | Async SQLAlchemy repository (get, list, create, update, delete) |
| `backend/app/services/auth_method.py` | Business logic: CRUD, token issuance, credential rotation, verification (bearer/basic/api_key) |
| `backend/app/routers/auth_methods.py` | REST CRUD + `/issue-token` + `/rotate` under `/api/v1/admin/auth/*` |
| `backend/app/routers/data.py` | Auth enforcement infrastructure: `_enforce_auth()` and `_write_access_log()` for Phase 4 integration |
| `backend/tests/test_auth_methods.py` | bcrypt/JWT unit tests + schema validation + API integration tests |

#### API Surface
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/admin/auth/` | List auth methods (`?active_only=true`) |
| POST | `/api/v1/admin/auth/` | Create auth method (201) |
| POST | `/api/v1/admin/auth/with-key` | Create API key method, returns key (201) |
| GET | `/api/v1/admin/auth/{id}` | Get single auth method |
| PUT | `/api/v1/admin/auth/{id}` | Update auth method |
| DELETE | `/api/v1/admin/auth/{id}` | Delete auth method (204) |
| POST | `/api/v1/admin/auth/{id}/issue-token` | Issue JWT for bearer method |
| POST | `/api/v1/admin/auth/{id}/rotate` | Rotate signing secret or API key |

#### Security
- Passwords hashed with bcrypt (never returned in API responses)
- Bearer signing secrets encrypted with Fernet before storage in `config_json`
- API keys shown once only on creation/rotation
- JWT tokens stateless — not stored server-side, verified via signing secret
- Token expiry enforced via `exp` claim
- All three auth types supported: Bearer JWT, Basic Auth, API Key

#### Frontend
| File | Purpose |
|------|---------|
| `frontend/src/types/auth_method.ts` | TypeScript interfaces matching API contract |
| `frontend/src/lib/api.ts` | Axios-based `authMethodsApi` client |
| `frontend/src/components/auth/AuthMethodForm.tsx` | Create/edit form with type-specific fields |
| `frontend/src/pages/AuthMethodsPage.tsx` | List table + create/edit/delete/issue/rotate dialogs |

#### Checks
- `ruff check .` — clean
- `mypy .` — clean
- `pytest -k "not integration"` — all passed
- `eslint` — clean
- `prettier --check` — clean
- `tsc -b && vite build` — clean

---

## Phase 4: Module 2 - API Creation Wizard End-to-End — COMPLETE

**Completed:** 2026-03-05

### Goals
Deliver the core wizard that converts parameterized SQL into deployable versioned data endpoints.

### Delivered

#### Backend
| File | Purpose |
|------|---------|
| `backend/app/schemas/endpoint.py` | `EndpointCreate` / `EndpointUpdate` / `EndpointResponse` / `SqlPreviewRequest` / `SqlPreviewResponse` / `ParamDescriptor` + SQL safety validation + bind parameter extraction |
| `backend/app/repositories/endpoint.py` | Async SQLAlchemy repository (get_all, get_by_id, get_by_name, get_by_path, create, update, delete) |
| `backend/app/services/endpoint.py` | Business logic: CRUD, uniqueness (name + path), connection validation, SQL preview orchestration, column map handling |
| `backend/app/routers/endpoints.py` | REST CRUD + `/preview` under `/api/v1/admin/endpoints/*` |
| `backend/app/sql/__init__.py` | SQL execution module |
| `backend/app/sql/executor.py` | Oracle SQL execution engine via python-oracledb with query timeout, thread delegation, structured logging |
| `backend/app/routers/data.py` | **Upgraded from Phase 3 stub**: Dynamic endpoint resolution, auth enforcement, parameter coercion, column mapping, access logging |
| `backend/tests/test_endpoints.py` | SQL safety unit tests + schema validation + bind parameter extraction + API integration tests |

#### Admin API Surface
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/admin/endpoints/` | List endpoints (`?active_only=true`) |
| POST | `/api/v1/admin/endpoints/` | Create endpoint (201) |
| GET | `/api/v1/admin/endpoints/{id}` | Get single endpoint |
| PUT | `/api/v1/admin/endpoints/{id}` | Update endpoint |
| DELETE | `/api/v1/admin/endpoints/{id}` | Delete endpoint (204) |
| POST | `/api/v1/admin/endpoints/preview` | Preview SQL execution (sample results) |

#### Dynamic Data API
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/data/{path}` | Execute endpoint query, enforce auth, return JSON data with metadata |

#### SQL Safety
- Named bind variables (`:param_name`) extracted and validated
- Unsafe interpolation patterns rejected (string concat, f-strings, template literals, PL/SQL concat)
- Parameters validated and coerced through typed `ParamDescriptor` schemas
- All SQL executed via python-oracledb with configurable query timeout

#### Data Endpoint Features
- Dynamic path-based endpoint resolution (no service restart needed)
- Per-endpoint auth enforcement (bearer/basic/api_key via Phase 3 infrastructure)
- Parameter extraction from query string with type coercion (string/integer/float/boolean)
- Required parameter validation with defaults support
- Column rename mapping (`column_map_json`)
- Deprecation headers (`Deprecation: true`, `Sunset`) for deprecated endpoints
- Access logging for all requests (success, auth failure, parameter errors, query errors)
- Response metadata: row_count, query_duration_ms, endpoint path, version, data_strategy

#### Frontend
| File | Purpose |
|------|---------|
| `frontend/src/types/endpoint.ts` | TypeScript interfaces matching API contract |
| `frontend/src/lib/api.ts` | Axios-based `endpointsApi` client (CRUD + preview) |
| `frontend/src/components/endpoints/SqlEditor.tsx` | CodeMirror 6 SQL editor with syntax highlighting and dark theme |
| `frontend/src/components/endpoints/EndpointWizard.tsx` | Multi-step wizard: Connection → SQL → Parameters → Auth & Config → Review & Publish |
| `frontend/src/pages/EndpointsPage.tsx` | List table + wizard + edit/delete dialogs + URL copy/open actions |
| `frontend/src/pages/DashboardPage.tsx` | Updated with endpoints count card |
| `frontend/src/components/Layout.tsx` | Updated with API Endpoints nav item |

#### Checks
- `ruff check .` — clean
- `mypy .` — clean (50 files, 0 errors)
- `pytest -k "not integration"` — 57 passed
- `eslint` — clean
- `prettier --check` — clean
- `tsc -b && vite build` — clean

---

## Phase 5: Module 4 - Scheduling + Snapshot Cache End-to-End — PENDING

## Phase 6: Module 5 - Settings + Health Dashboard End-to-End — PENDING

## Phase 7: Integration Hardening — PENDING
