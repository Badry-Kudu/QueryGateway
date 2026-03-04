.PHONY: help check check-backend check-frontend docker-build docker-up docker-down \
        backend-dev frontend-dev backend-setup frontend-setup

# Default target
help:
	@echo "DB2API-Exposure — available targets:"
	@echo ""
	@echo "  make setup           Install all dependencies (backend + frontend)"
	@echo "  make check           Run all linting, type-checks, and tests"
	@echo "  make check-backend   Run backend checks (ruff, mypy, pytest)"
	@echo "  make check-frontend  Run frontend checks (eslint, prettier, vitest)"
	@echo "  make docker-build    Build all Docker images"
	@echo "  make docker-up       Start all services via docker compose"
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

docker-up:
	docker compose up -d

docker-down:
	docker compose down

# ─── Dev servers ─────────────────────────────────────────────────────────────

backend-dev:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload

frontend-dev:
	cd frontend && npm run dev
