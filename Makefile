# ============================================================
# DevOps Assistant - Project Makefile
# ============================================================

.DEFAULT_GOAL := help

PYTHON ?= python3
VENV := backend/venv

ifeq ($(OS),Windows_NT)
BACKEND_PY := venv/Scripts/python.exe
VENV_PY := $(VENV)/Scripts/python.exe
else
BACKEND_PY := venv/bin/python
VENV_PY := $(VENV)/bin/python
endif

.PHONY: help \
	setup setup-backend setup-frontend \
	dev dev-backend dev-frontend \
	test test-backend \
	lint lint-backend lint-frontend \
	build build-frontend \
	docker-up docker-down docker-logs docker-clean \
	clean clean-python clean-node clean-share

help:
	@echo "DevOps Assistant commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup             Install backend and frontend dependencies"
	@echo "  make setup-backend     Create backend venv and install Python packages"
	@echo "  make setup-frontend    Install frontend npm packages"
	@echo ""
	@echo "Run:"
	@echo "  make dev               Start the full stack with Docker Compose"
	@echo "  make dev-backend       Start FastAPI on http://localhost:8000"
	@echo "  make dev-frontend      Start Vite on http://localhost:5173"
	@echo ""
	@echo "Quality:"
	@echo "  make test              Run backend tests"
	@echo "  make lint              Run backend and frontend linters"
	@echo "  make build             Build the frontend"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up         Build and start all services"
	@echo "  make docker-down       Stop all services"
	@echo "  make docker-logs       Tail service logs"
	@echo "  make docker-clean      Remove containers, volumes, and local images"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean             Remove generated dependency/build/cache folders"
	@echo "  make clean-python      Remove backend virtualenvs and Python caches"
	@echo "  make clean-node        Remove frontend node_modules and build caches"
	@echo "  make clean-share       Clean generated files before sharing the project"

# Setup
setup: setup-backend setup-frontend

setup-backend:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PY) -m pip install --upgrade pip
	$(VENV_PY) -m pip install -r backend/requirements.txt

setup-frontend:
	cd frontend && npm install

# Run locally
dev: docker-up

dev-backend:
	cd backend && $(BACKEND_PY) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

dev-frontend:
	cd frontend && npm run dev

# Quality checks
test: test-backend

test-backend:
	cd backend && $(BACKEND_PY) -m pytest tests -v --cov=app --cov-report=term-missing

lint: lint-backend lint-frontend

lint-backend:
	cd backend && $(BACKEND_PY) -m flake8 app --max-line-length=120
	cd backend && $(BACKEND_PY) -m mypy app --ignore-missing-imports

lint-frontend:
	cd frontend && npm run lint

build: build-frontend

build-frontend:
	cd frontend && npm run build

# Docker
docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-clean:
	docker compose down -v --rmi local

# Cleanup
clean: clean-python clean-node

clean-python:
	$(PYTHON) -c "import shutil; [shutil.rmtree(path, ignore_errors=True) for path in ('backend/.venv', 'backend/venv', 'backend/.pytest_cache', 'backend/.mypy_cache')]"
	find backend -type d \( -name '__pycache__' -o -name '.pytest_cache' -o -name '.mypy_cache' \) -prune -exec rm -rf {} +
	find backend -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

clean-node:
	$(PYTHON) -c "import shutil; [shutil.rmtree(path, ignore_errors=True) for path in ('frontend/node_modules', 'frontend/dist', 'frontend/.vite', 'frontend/.eslintcache')]"

clean-share: clean
	@echo "Generated Python and Node files removed. The project is ready to share."
