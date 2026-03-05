# DB2API-Exposure

A self-hosted platform to expose Oracle SQL queries as secure, dynamic REST endpoints with optional scheduled snapshot caching.

## Platform Support

- Development: Windows and Ubuntu/Linux
- Deployment: Ubuntu/Linux (recommended)
- Docker workflow: supported on both Windows (Docker Desktop) and Ubuntu/Linux

## Quick Start

```sh
# Install dependencies
make setup

# Run checks
make check

# Start with Docker
cp .env.example .env   # Edit JWT_SECRET_KEY
make docker-up
```

- Backend API: `http://localhost:8000` — interactive docs at `/api/docs`
- Frontend SPA: `http://localhost:80`

## Local Run (Without Docker)

### Windows (PowerShell)

```powershell
# Backend
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
# edit .env as needed, then run:
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
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
# edit .env as needed, then run:
uvicorn app.main:app --reload
```

```bash
# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Local URLs

- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/api/docs`
- Frontend dev server: `http://localhost:5173`

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
