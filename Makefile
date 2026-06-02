# ============================================================
# Smart DevOps Assistant - Developer Makefile
# ============================================================

.DEFAULT_GOAL := help

SHELL := /bin/sh
PYTHON ?= $(shell if command -v python3.11 >/dev/null 2>&1; then echo python3.11; elif command -v python3 >/dev/null 2>&1; then echo python3; elif command -v python >/dev/null 2>&1; then echo python; else echo python3; fi)
BACKEND_DIR := backend
FRONTEND_DIR := frontend
BACKEND_VENV := $(BACKEND_DIR)/venv
BACKEND_PY := $(BACKEND_VENV)/bin/python
PIP := $(BACKEND_PY) -m pip
NPM := npm
COMPOSE := $(shell if docker compose version >/dev/null 2>&1; then echo "docker compose"; elif command -v docker-compose >/dev/null 2>&1; then echo "docker-compose"; else echo ""; fi)

.PHONY: help setup backend-install frontend-install dev dev-build backend frontend train-model \
	test test-backend test-frontend lint lint-backend lint-frontend format format-backend format-frontend \
	build docker-build clean docker-down docker-logs reset

## Show all available commands.
help:
	@echo "Smart DevOps Assistant commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup              Install backend and frontend dependencies"
	@echo "  make backend-install    Create backend venv and install requirements.txt"
	@echo "  make frontend-install   Install frontend npm dependencies"
	@echo ""
	@echo "Run:"
	@echo "  make dev                Start full project with Docker Compose"
	@echo "  make dev-build          Build and start full project with Docker Compose"
	@echo "  make backend            Start FastAPI locally on http://localhost:8000"
	@echo "  make frontend           Start Vite locally on http://localhost:5173"
	@echo "  make train-model        Train the CI/CD failure classification model"
	@echo ""
	@echo "Quality:"
	@echo "  make test               Run backend and frontend tests where configured"
	@echo "  make test-backend       Run backend pytest suite"
	@echo "  make test-frontend      Run frontend tests if package.json defines test"
	@echo "  make lint               Run configured backend/frontend linters"
	@echo "  make format             Run configured backend/frontend formatters"
	@echo "  make build              Build frontend production bundle"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build       Build Docker images"
	@echo "  make docker-down        Stop Docker Compose services"
	@echo "  make docker-logs        Show Docker Compose logs"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean              Remove caches, builds, and local dependency installs"
	@echo "  make reset              Stop containers and remove caches/builds/dependencies"

## Install backend and frontend dependencies if their manifests exist.
setup: backend-install frontend-install

## Create backend virtualenv and install Python dependencies.
backend-install:
	@if [ ! -f "$(BACKEND_DIR)/requirements.txt" ]; then echo "No backend/requirements.txt found; skipping backend install."; exit 0; fi
	$(PYTHON) -m venv $(BACKEND_VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt

## Install frontend npm dependencies inside frontend/.
frontend-install:
	@if [ ! -f "$(FRONTEND_DIR)/package.json" ]; then echo "No frontend/package.json found; skipping frontend install."; exit 0; fi
	@cd $(FRONTEND_DIR) && if [ -f package-lock.json ]; then $(NPM) ci; else $(NPM) install; fi

## Start the full project using Docker Compose.
dev:
	@if [ -z "$(COMPOSE)" ]; then echo "Docker Compose is not available."; exit 1; fi
	$(COMPOSE) up -d

## Build and start the full project using Docker Compose.
dev-build:
	@if [ -z "$(COMPOSE)" ]; then echo "Docker Compose is not available."; exit 1; fi
	$(COMPOSE) up -d --build

## Start FastAPI locally.
backend:
	@if [ ! -x "$(BACKEND_PY)" ]; then echo "Backend venv missing. Run: make backend-install"; exit 1; fi
	@cd $(BACKEND_DIR) && ../$(BACKEND_PY) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

## Start the React/Vite frontend locally.
frontend:
	@if [ ! -f "$(FRONTEND_DIR)/package.json" ]; then echo "No frontend/package.json found."; exit 1; fi
	@cd $(FRONTEND_DIR) && $(NPM) run dev

## Train the CI/CD failure classification model.
train-model:
	@if [ ! -x "$(BACKEND_PY)" ]; then echo "Backend venv missing. Run: make backend-install"; exit 1; fi
	@cd $(BACKEND_DIR) && ../$(BACKEND_PY) app/ml/train_failure_model.py

## Run backend and frontend tests where configured.
test: test-backend test-frontend

## Run backend pytest suite.
test-backend:
	@if [ ! -x "$(BACKEND_PY)" ]; then echo "Backend venv missing. Run: make backend-install"; exit 1; fi
	@cd $(BACKEND_DIR) && ../$(BACKEND_PY) -m pytest tests -q

## Run frontend tests only if package.json defines a test script.
test-frontend:
	@if [ ! -f "$(FRONTEND_DIR)/package.json" ]; then echo "No frontend/package.json found; skipping frontend tests."; exit 0; fi
	@cd $(FRONTEND_DIR) && if node -e "process.exit(require('./package.json').scripts && require('./package.json').scripts.test ? 0 : 1)"; then $(NPM) test; else echo "No frontend test script configured; skipping."; fi

## Run configured backend and frontend lint commands.
lint: lint-backend lint-frontend

## Run backend linters if installed in the backend virtualenv.
lint-backend:
	@if [ ! -x "$(BACKEND_PY)" ]; then echo "Backend venv missing; skipping backend lint."; exit 0; fi
	@cd $(BACKEND_DIR) && if ../$(BACKEND_PY) -m flake8 --version >/dev/null 2>&1; then ../$(BACKEND_PY) -m flake8 app tests --max-line-length=120; else echo "flake8 not installed; skipping."; fi
	@cd $(BACKEND_DIR) && if ../$(BACKEND_PY) -m mypy --version >/dev/null 2>&1; then ../$(BACKEND_PY) -m mypy app --ignore-missing-imports; else echo "mypy not installed; skipping."; fi

## Run frontend lint script if configured.
lint-frontend:
	@if [ ! -f "$(FRONTEND_DIR)/package.json" ]; then echo "No frontend/package.json found; skipping frontend lint."; exit 0; fi
	@cd $(FRONTEND_DIR) && if node -e "process.exit(require('./package.json').scripts && require('./package.json').scripts.lint ? 0 : 1)"; then $(NPM) run lint; else echo "No frontend lint script configured; skipping."; fi

## Run configured formatters.
format: format-backend format-frontend

## Run backend formatter if black or ruff is installed.
format-backend:
	@if [ ! -x "$(BACKEND_PY)" ]; then echo "Backend venv missing; skipping backend format."; exit 0; fi
	@cd $(BACKEND_DIR) && if ../$(BACKEND_PY) -m black --version >/dev/null 2>&1; then ../$(BACKEND_PY) -m black app tests; elif ../$(BACKEND_PY) -m ruff --version >/dev/null 2>&1; then ../$(BACKEND_PY) -m ruff format app tests; else echo "No backend formatter configured; skipping."; fi

## Run frontend formatter script if configured.
format-frontend:
	@if [ ! -f "$(FRONTEND_DIR)/package.json" ]; then echo "No frontend/package.json found; skipping frontend format."; exit 0; fi
	@cd $(FRONTEND_DIR) && if node -e "process.exit(require('./package.json').scripts && require('./package.json').scripts.format ? 0 : 1)"; then $(NPM) run format; else echo "No frontend format script configured; skipping."; fi

## Build frontend production bundle.
build:
	@if [ ! -f "$(FRONTEND_DIR)/package.json" ]; then echo "No frontend/package.json found; skipping frontend build."; exit 0; fi
	@cd $(FRONTEND_DIR) && $(NPM) run build

## Build Docker images if Docker Compose is available.
docker-build:
	@if [ -z "$(COMPOSE)" ]; then echo "Docker Compose is not available."; exit 1; fi
	$(COMPOSE) build

## Remove generated caches, build output, and local dependency installs. Keeps source, docs, env files, datasets, models, and DB volumes.
clean:
	@find . \
		\( -path "./.git" -o -path "./$(BACKEND_VENV)" -o -path "./$(FRONTEND_DIR)/node_modules" -o -path "./.venv" -o -path "./venv" -o -path "./postgres_data" -o -path "./redis_data" \) -prune \
		-o -type d \( -name "__pycache__" -o -name ".pytest_cache" -o -name ".mypy_cache" -o -name ".ruff_cache" -o -name "htmlcov" \) -prune -exec rm -rf {} +
	@find . \
		\( -path "./.git" -o -path "./$(BACKEND_VENV)" -o -path "./$(FRONTEND_DIR)/node_modules" -o -path "./.venv" -o -path "./venv" -o -path "./postgres_data" -o -path "./redis_data" \) -prune \
		-o -type f \( -name "*.pyc" -o -name "*.pyo" -o -name ".coverage*" -o -name "coverage.xml" -o -name ".DS_Store" -o -name "*.log" \) -delete
	@rm -rf $(FRONTEND_DIR)/dist $(FRONTEND_DIR)/build
	@rm -rf dist build htmlcov
	@rm -rf $(FRONTEND_DIR)/node_modules $(BACKEND_VENV) .venv venv
	@echo "Removed generated caches, build outputs, and local dependency installs."

## Stop Docker Compose services.
docker-down:
	@if [ -z "$(COMPOSE)" ]; then echo "Docker Compose is not available."; exit 1; fi
	$(COMPOSE) down

## Show Docker Compose logs.
docker-logs:
	@if [ -z "$(COMPOSE)" ]; then echo "Docker Compose is not available."; exit 1; fi
	$(COMPOSE) logs -f

## Stop containers and remove generated files/dependencies. Does not delete Docker volumes or databases.
reset: docker-down clean
	@echo "Reset complete. Docker volumes and database files were not removed."
