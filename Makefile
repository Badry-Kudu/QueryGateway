.PHONY: help check check-backend check-frontend docker-build docker-migrate docker-up docker-down \
        backend-dev frontend-dev backend-setup frontend-setup

# Default target
help:
	@echo "QueryGateway — available targets:"
	@echo ""
	@echo "  make setup           Install all dependencies (backend + frontend)"
	@echo "  make check           Run all linting, type-checks, and tests"
	@echo "  make check-backend   Run backend checks (ruff, mypy, pytest)"
	@echo "  make check-frontend  Run frontend checks (eslint, prettier, vitest)"
	@echo "  make docker-build    Build all Docker images"
	@echo "  make docker-migrate  Run the one-shot Docker migration service"
	@echo "  make docker-up       Run migrations and start all services via docker compose"
	@echo "  make docker-down     Stop all services"
	@echo "  make backend-dev     Start backend dev server"
	@echo "  make frontend-dev    Start frontend dev server"

# ─── Setup ───────────────────────────────────────────────────────────────────

setup: backend-setup frontend-setup

backend-setup:
	cd backend && python -m venv .venv && \
	. .venv/bin/activate && \
	pip install --upgrade pip && \
	pip install -r requirements.txt

frontend-setup:
	cd frontend && npm install

# ─── Checks ──────────────────────────────────────────────────────────────────

check: check-backend check-frontend docker-build

check-backend:
	cd backend && . .venv/bin/activate && \
	ruff check . && \
	mypy . && \
	pytest

check-frontend:
	cd frontend && \
	npm run eslint && \
	npm run prettier:check && \
	npm run test

# ─── Docker ──────────────────────────────────────────────────────────────────

docker-build:
	docker compose build

docker-migrate:
	docker compose up --build --force-recreate migrate

docker-up:
	docker compose up -d

docker-down:
	docker compose down

# ─── Dev servers ─────────────────────────────────────────────────────────────

backend-dev:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload

frontend-dev:
	cd frontend && npm run dev
