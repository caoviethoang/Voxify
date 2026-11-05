VENV ?= $(shell pwd)/.venv
RUFF ?= $(shell which ruff 2>/dev/null || echo $(VENV)/bin/ruff)
MYPY ?= $(shell which mypy 2>/dev/null || echo $(VENV)/bin/mypy)
PYTEST ?= $(shell which pytest 2>/dev/null || echo $(VENV)/bin/pytest)

.PHONY: help up down lint test coverage e2e format clean

help:
	@echo "Voxify Development Commands:"
	@echo "  make up          - Start all docker containers (backend, frontend, postgres, redis, nginx)"
	@echo "  make down        - Stop and remove docker containers"
	@echo "  make lint        - Run backend ruff + mypy, and frontend eslint"
	@echo "  make test        - Run backend pytest and frontend vitest"
	@echo "  make coverage    - Run backend and frontend coverage reports"
	@echo "  make e2e         - Run Playwright E2E tests"
	@echo "  make format      - Auto-format code using ruff and prettier"
	@echo "  make clean       - Remove cache, coverage, and temporary build files"

up:
	docker compose up -d

down:
	docker compose down

lint:
	@echo "==> Linting backend with Ruff..."
	cd backend && $(RUFF) check app tests
	@echo "==> Type checking backend with Mypy..."
	cd backend && $(MYPY) --config-file mypy.ini app
	@echo "==> Linting frontend with ESLint..."
	cd frontend && npm run lint

test:
	@echo "==> Running backend Pytest..."
	cd backend && $(PYTEST)
	@echo "==> Running frontend Vitest..."
	cd frontend && npm run test

coverage:
	@echo "==> Running backend Pytest with Coverage (Minimum 80% total, 90% CreditService)..."
	cd backend && $(PYTEST) --cov=app --cov-report=term-missing --cov-report=xml:coverage.xml --cov-fail-under=80
	@echo "==> Running frontend Vitest Coverage..."
	cd frontend && npm run test:coverage

e2e:
	@echo "==> Running Playwright E2E Tests..."
	cd frontend && npx playwright test -c ../e2e/playwright.config.ts

format:
	@echo "==> Formatting backend..."
	cd backend && $(RUFF) format app tests
	@echo "==> Formatting frontend..."
	cd frontend && npm run format

clean:
	rm -rf backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache backend/.coverage backend/coverage.xml
	rm -rf frontend/node_modules/.vite frontend/dist frontend/coverage
	rm -rf e2e/playwright-report e2e/test-results
