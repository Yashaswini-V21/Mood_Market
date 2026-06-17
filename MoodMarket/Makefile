# ============================================================================
# Mood Market — Developer Makefile
# ============================================================================
# Usage:
#   make help          List all available commands
#   make run           Start the dev server (hot reload)
#   make test          Run the full test suite with coverage
#   make lint          Run flake8 + mypy
#   make docker-up     Spin up the full 9-service Docker stack
#   make docker-down   Tear down all containers
# ============================================================================

.PHONY: help run test lint format type-check clean docker-up docker-down \
        docker-build docker-logs shell-backend shell-db migrations coverage

PYTHON      := python3
PIP         := pip3
BACKEND_DIR := backend
ML_DIR      := ml
TEST_DIR    := test
PYTHONPATH  := $(BACKEND_DIR):$(ML_DIR)

# ── Default target ────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  ╔══════════════════════════════════════════════════╗"
	@echo "  ║           Mood Market — Dev Commands             ║"
	@echo "  ╚══════════════════════════════════════════════════╝"
	@echo ""
	@echo "  Development:"
	@echo "    make run            Start FastAPI dev server (hot reload)"
	@echo "    make run-frontend   Start Vite dev server"
	@echo "    make shell-backend  Open a shell inside the backend container"
	@echo "    make shell-db       Open a psql shell in the Postgres container"
	@echo ""
	@echo "  Testing:"
	@echo "    make test           Run all tests with coverage"
	@echo "    make test-unit      Run unit tests only"
	@echo "    make test-int       Run integration tests only"
	@echo "    make coverage       Open HTML coverage report in browser"
	@echo ""
	@echo "  Code Quality:"
	@echo "    make lint           Flake8 syntax + style check"
	@echo "    make type-check     Mypy static type analysis"
	@echo "    make format         Black + isort autoformat"
	@echo "    make security       Bandit + Safety vulnerability scan"
	@echo ""
	@echo "  Docker:"
	@echo "    make docker-up      Build and start all 9 services"
	@echo "    make docker-down    Stop and remove all containers"
	@echo "    make docker-build   Rebuild the backend image only"
	@echo "    make docker-logs    Tail logs from all services"
	@echo ""
	@echo "  Database:"
	@echo "    make migrations     Run all pending SQL migrations"
	@echo "    make clean          Remove .pyc / __pycache__ / coverage artifacts"
	@echo ""

# ── Development ───────────────────────────────────────────────────────────────
run:
	@echo "▶  Starting MoodMarket API (hot reload)..."
	PYTHONPATH=$(PYTHONPATH) uvicorn $(BACKEND_DIR)/main:app \
	  --host 0.0.0.0 --port 8000 --reload \
	  --reload-dir $(BACKEND_DIR) --reload-dir $(ML_DIR)

run-frontend:
	@echo "▶  Starting Vite frontend dev server..."
	cd frontend && npm run dev

# ── Testing ───────────────────────────────────────────────────────────────────
test:
	@echo "▶  Running full test suite with coverage..."
	PYTHONPATH=$(PYTHONPATH) \
	ENVIRONMENT=test ENV=test \
	TIMESCALEDB_URI=sqlite+aiosqlite:///:memory: \
	REDIS_URI=redis://localhost:6379/9 \
	pytest ./ \
	  --cov=./ \
	  --cov-report=term-missing \
	  --cov-report=html:htmlcov \
	  --cov-config=$(BACKEND_DIR)/.coveragerc \
	  -q --tb=short

test-unit:
	@echo "▶  Running unit tests..."
	PYTHONPATH=$(PYTHONPATH) ENVIRONMENT=test ENV=test \
	pytest $(TEST_DIR)/unit/ -q --tb=short

test-int:
	@echo "▶  Running integration tests..."
	PYTHONPATH=$(PYTHONPATH) ENVIRONMENT=test ENV=test \
	pytest $(TEST_DIR)/integration/ -q --tb=short

coverage:
	@echo "▶  Opening coverage report..."
	open htmlcov/index.html 2>/dev/null || start htmlcov/index.html

# ── Code Quality ─────────────────────────────────────────────────────────────
lint:
	@echo "▶  Linting with flake8..."
	flake8 ./ \
	  --count --select=E9,F63,F7,F82 --show-source --statistics \
	  --exclude=.git,__pycache__,frontend,htmlcov,dist,.venv
	@echo "▶  Style check (soft)..."
	flake8 ./ \
	  --count --exit-zero --max-complexity=12 --max-line-length=127 \
	  --exclude=.git,__pycache__,frontend,htmlcov,dist,.venv

type-check:
	@echo "▶  Running mypy..."
	mypy ./ --ignore-missing-imports \
	  --exclude '(frontend|htmlcov|dist)' || true

format:
	@echo "▶  Formatting with black + isort..."
	black ./ --line-length 127 \
	  --exclude '/(frontend|htmlcov|dist|__pycache__|\.git)/'
	isort ./ --profile black --line-length 127 \
	  --skip-glob '**/frontend/**' --skip-glob '**/htmlcov/**'

security:
	@echo "▶  Running Bandit security scan..."
	bandit -r MoodMarket/backend MoodMarket/ml -ll -q
	@echo "▶  Running Safety dependency check..."
	safety check -r $(BACKEND_DIR)/requirements.txt --short-report || true

# ── Docker ────────────────────────────────────────────────────────────────────
docker-up:
	@echo "▶  Building and starting all services..."
	docker compose -f backend/docker-compose.yml up --build -d
	@echo ""
	@echo "  ✓ Services started:"
	@echo "    API      → http://localhost:8000/docs"
	@echo "    Frontend → http://localhost:3000"
	@echo "    Grafana  → http://localhost:3001"
	@echo "    Flower   → http://localhost:5555"
	@echo "    Prometheus → http://localhost:9090"

docker-down:
	@echo "▶  Stopping all services..."
	docker compose -f backend/docker-compose.yml down

docker-build:
	@echo "▶  Rebuilding backend image..."
	docker compose -f backend/docker-compose.yml build backend

docker-logs:
	docker compose -f backend/docker-compose.yml logs -f

shell-backend:
	docker compose -f backend/docker-compose.yml \
	  exec backend /bin/bash

shell-db:
	docker compose -f backend/docker-compose.yml \
	  exec postgres psql -U postgres -d moodmarket

# ── Database ──────────────────────────────────────────────────────────────────
migrations:
	@echo "▶  Running database migrations..."
	PYTHONPATH=$(PYTHONPATH) \
	$(PYTHON) -c "import asyncio; from database import run_all_migrations; asyncio.run(run_all_migrations())"

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean:
	@echo "▶  Cleaning build artifacts..."
	find . -type d -name __pycache__ -not -path '*/.git/*' -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -not -path '*/.git/*' -delete 2>/dev/null || true
	find . -name "*.pyo" -not -path '*/.git/*' -delete 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml .mypy_cache .pytest_cache
	@echo "  ✓ Clean complete"
