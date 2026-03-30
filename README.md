# DB2API-Exposure

A self-hosted platform to expose Oracle SQL queries as secure, dynamic REST endpoints with optional scheduled snapshot caching.

## Platform Support

- Development: Windows and Ubuntu/Linux
- Deployment: Ubuntu/Linux (recommended)
- Docker workflow: supported on both Windows (Docker Desktop) and Ubuntu/Linux

> **Python version:** Python 3.12 or 3.13 is required. Python 3.14 is not yet supported — `asyncpg` does not have stable wheels for CPython 3.14. If you have Python 3.14 installed, install Python 3.12 or 3.13 and create the virtual environment with the correct interpreter: `py -3.12 -m venv .venv` (Windows) or `python3.12 -m venv .venv` (Linux).

## Quick Start

```sh
# Install dependencies
make setup

# Run checks
make check

# Start with Docker
cp .env.example .env   # Set JWT_SECRET_KEY and ENCRYPTION_KEY (see deployment.md for generation commands)
make docker-up
```

- Backend API: `http://localhost:8000` — interactive docs at `/api/docs`
- Frontend SPA: `http://localhost:80`

## Local Run (Without Docker)

> **Python version:** Use Python 3.12 or 3.13. Python 3.14 is not yet supported (`asyncpg` has no wheels for CPython 3.14).
>
> **Note (Windows):** `psycopg2-binary` may fail to build from source if PostgreSQL dev tools are not installed. The `requirements.txt` uses a relaxed pin (`>=2.9.9`) so pip selects a pre-built wheel automatically. Always run `pip install --upgrade pip` first.

### Windows (PowerShell)

```powershell
# Step 1 — Start PostgreSQL (skip if already running)
docker run -d --name db2api-pg `
  -e POSTGRES_USER=db2api -e POSTGRES_PASSWORD=db2api -e POSTGRES_DB=db2api `
  -p 5432:5432 postgres:16
# Wait ~5 seconds for PostgreSQL to initialize before continuing

# Step 2 — Backend
cd backend
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
# edit .env — set ENCRYPTION_KEY and JWT_SECRET_KEY before continuing

# Step 3 — Run database migrations
alembic upgrade head

# Step 4 — Start the backend
uvicorn app.main:app --reload
```

```powershell
# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Ubuntu/Linux (bash)

```bash
# Step 1 — Start PostgreSQL (skip if already running)
docker run -d --name db2api-pg \
  -e POSTGRES_USER=db2api -e POSTGRES_PASSWORD=db2api -e POSTGRES_DB=db2api \
  -p 5432:5432 postgres:16
# Wait ~5 seconds for PostgreSQL to initialize before continuing

# Step 2 — Backend
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
# edit .env — set ENCRYPTION_KEY and JWT_SECRET_KEY before continuing

# Step 3 — Run database migrations
alembic upgrade head

# Step 4 — Start the backend
uvicorn app.main:app --reload
```

```bash
# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Local URLs

- API docs (Swagger): `http://localhost:8000/api/docs`
- Health check: `http://localhost:8000/api/v1/admin/health/live`
- Frontend SPA: `http://localhost:5173` (start frontend dev server first — see above)

> **Note:** `http://localhost:8000/` returns 404 — the backend serves no root route. All API routes are under `/api/v1/`.

## Development

```sh
make backend-dev    # FastAPI dev server on :8000 (hot reload)
make frontend-dev   # Vite dev server on :5173 (proxy /api to :8000)
```

Note: `make` targets are POSIX-oriented and work natively on Ubuntu/Linux. On Windows, run the platform-specific commands above, or use WSL/Git Bash with `make`.

## Database Migrations

```sh
cd backend
# Apply all pending migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "describe change"

# Rollback one step
alembic downgrade -1
```

## Documentation

- [Architecture](docs/architecture.md)
- [Contributing](docs/contributing.md)
- [Conventions](docs/conventions.md)
- [Implementation Plan](project_plan.md)
- [Progress](docs/progress.md)

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic, APScheduler 3.x, PyJWT, bcrypt, structlog |
| Frontend | Vite 6, React 18, TypeScript, shadcn/ui, Tailwind CSS 3, Vitest |
| App DB | PostgreSQL 16 (asyncpg) |
| Data Source | Oracle (python-oracledb thin mode) |
| CI/CD | GitHub Actions — backend (ruff/mypy/pytest), frontend (eslint/prettier/vitest), Docker build |
