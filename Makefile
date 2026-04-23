# ============================================================
# DevOps Assistant — Project Makefile
# ============================================================
.PHONY: help setup-backend setup-frontend dev-backend dev-frontend \
        docker-up docker-down docker-logs test lint clean

PYTHON  ?= python3.11
VENV    := backend/.venv
PIP     := $(VENV)/bin/pip
PYTEST  := $(VENV)/bin/pytest
UVICORN := $(VENV)/bin/uvicorn

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Backend ──────────────────────────────────────────────────
setup-backend: ## Create Python 3.11 venv and install requirements
	cd backend && bash setup.sh

dev-backend: ## Run FastAPI with hot-reload (requires venv)
	@cd backend && $(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --reload

lint-backend: ## Lint backend with flake8 + mypy
	cd backend && $(VENV)/bin/flake8 app --max-line-length=120
	cd backend && $(VENV)/bin/mypy app --ignore-missing-imports

test-backend: ## Run backend tests with coverage
	cd backend && $(PYTEST) tests/ -v --cov=app --cov-report=term-missing

# ── Frontend ─────────────────────────────────────────────────
setup-frontend: ## Install frontend npm deps
	cd frontend && npm install

dev-frontend: ## Run Vite dev server
	cd frontend && npm run dev

lint-frontend: ## Lint frontend with ESLint
	cd frontend && npm run lint

build-frontend: ## Production build
	cd frontend && npm run build

# ── Docker ───────────────────────────────────────────────────
docker-up: ## Start all services via Docker Compose
	docker compose up -d --build

docker-down: ## Stop all services
	docker compose down

docker-logs: ## Tail logs for all containers
	docker compose logs -f

docker-clean: ## Remove containers, volumes, and images
	docker compose down -v --rmi local

# ── Combined ─────────────────────────────────────────────────
setup: setup-backend setup-frontend ## Set up both backend and frontend

lint: lint-backend lint-frontend ## Lint everything

test: test-backend ## Run all tests

clean: ## Remove venv and node_modules
	rm -rf backend/.venv frontend/node_modules frontend/dist
