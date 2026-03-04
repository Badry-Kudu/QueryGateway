# Architecture Overview

## System Components

```
┌───────────────────────────────────────────────────────────────────┐
│                        DB2API-Exposure                            │
│                                                                   │
│  ┌──────────────┐    HTTP     ┌──────────────────────────────┐   │
│  │   Frontend   │ ──────────▶ │         Backend (FastAPI)    │   │
│  │  (React SPA) │            │                              │   │
│  │  Port: 80    │            │  /api/v1/admin/*  (admin)    │   │
│  └──────────────┘            │  /api/v1/data/*   (consumer) │   │
│                              │                              │   │
│                              │  ┌──────────────────────┐   │   │
│                              │  │   APScheduler 3.x    │   │   │
│                              │  │   (in-process)       │   │   │
│                              │  └──────────┬───────────┘   │   │
│                              └─────────────┼───────────────┘   │
│                                            │                    │
│              ┌─────────────────────────────┴──────────┐        │
│              │                                         │        │
│  ┌───────────▼───────┐                  ┌─────────────▼──────┐ │
│  │    PostgreSQL      │                  │  Oracle Database   │ │
│  │  (app metadata,   │                  │  (user data source)│ │
│  │   job store,      │                  │                    │ │
│  │   snapshots)      │                  │  python-oracledb   │ │
│  └───────────────────┘                  └────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

## Route Namespaces

| Namespace | Purpose | Who calls it |
|-----------|---------|--------------|
| `/api/v1/admin/*` | Manage connections, auth, endpoints, schedules, settings, health | Admin SPA |
| `/api/v1/data/*` | Serve dynamic data from live queries or snapshots | API consumers |

## Key Design Decisions

### SQL Safety
All user-defined SQL is executed via SQLAlchemy `text()` with named bind parameters (`:param_name`). String interpolation of user input is prohibited at all layers. Bind values are validated through typed Pydantic schemas before reaching the query executor.

### Authentication
- Admin API: session-based or JWT Bearer (TBD per Phase 1).
- Data endpoints: per-endpoint configurable auth — Bearer token, Basic Auth, or API key. Middleware resolves the policy from endpoint metadata at request time.
- Credentials are hashed with `bcrypt`; tokens are issued/verified with `PyJWT`.

### Scheduler
APScheduler 3.x runs in-process with a PostgreSQL job store, ensuring job persistence across restarts. Execution telemetry (start time, duration, row count, status, errors) is written to the app DB and exposed through admin APIs.

### Snapshot Cache
Scheduled endpoints can serve results from a PostgreSQL JSONB snapshot rather than executing live queries. Freshness metadata is returned in responses. Stale snapshot fallback behavior is configurable per endpoint.

### Configuration
Pydantic Settings v2 loads all configuration from environment variables (`.env` in development, injected secrets in production). No hardcoded configuration values in source code.

### Logging
`structlog` emits structured JSON with mandatory correlation fields (`request_id`, `user`, `endpoint`, `status`, `duration_ms`, `event`). Sensitive fields are redacted at middleware level before emission.

## Directory Layout

```
DB2API-Exposure/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app factory, CORS, router registration
│   │   ├── config.py        # Pydantic Settings
│   │   ├── models/          # SQLAlchemy models (Phase 1+)
│   │   ├── routers/         # Route handlers (Phase 1+)
│   │   ├── services/        # Business logic layer (Phase 1+)
│   │   ├── repositories/    # DB access layer (Phase 1+)
│   │   ├── auth/            # JWT + bcrypt utilities (Phase 3+)
│   │   ├── scheduler/       # APScheduler integration (Phase 5+)
│   │   └── sql/             # SQL execution and validation (Phase 4+)
│   ├── alembic/             # Migration environment (Phase 1+)
│   ├── tests/               # Pytest test suite
│   ├── requirements.txt
│   └── pyproject.toml       # ruff, mypy, pytest config
├── frontend/
│   ├── src/
│   │   ├── main.tsx         # React app entry
│   │   ├── App.tsx          # Root component / router (Phase 1+)
│   │   ├── components/      # shadcn/ui + custom components (Phase 2+)
│   │   ├── pages/           # Route-level page components (Phase 2+)
│   │   ├── lib/             # API clients, utilities (Phase 2+)
│   │   └── test/            # Vitest setup
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── package.json
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── docs/
│   ├── architecture.md      # This file
│   ├── conventions.md       # Coding standards
│   └── contributing.md      # Onboarding guide
├── .github/
│   ├── workflows/
│   │   ├── backend.yml      # Backend CI
│   │   ├── frontend.yml     # Frontend CI
│   │   └── docker.yml       # Docker build CI
│   └── instructions/        # AI assistant context files
├── docker-compose.yml
└── .env.example
```
