PYTHON ?= python3
BACKEND_DIR = backend
INGESTION_DIR = backend/ingestion

.PHONY: help setup install install-dev lint format test run docker-build docker-up docker-down docker-logs docker-restart docker-clean migrate

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Virtual Environment Setup
setup: ## Setup virtual environments and copy env files
	@./scripts/setup_venv.sh

# Installation
install: ## Install backend API dependencies
	cd $(BACKEND_DIR) && $(PYTHON) -m pip install -r requirements.txt

install-ingestion: ## Install ingestion service dependencies
	cd $(INGESTION_DIR) && $(PYTHON) -m pip install -r requirements.txt

install-dev: ## Install backend API dev dependencies
	cd $(BACKEND_DIR) && $(PYTHON) -m pip install -r requirements-dev.txt

install-dev-ingestion: ## Install ingestion service dev dependencies
	cd $(INGESTION_DIR) && $(PYTHON) -m pip install -r requirements-dev.txt

# Code Quality
lint: ## Lint backend API code
	ruff check $(BACKEND_DIR)

lint-ingestion: ## Lint ingestion service code
	ruff check $(INGESTION_DIR)

format: ## Format backend API code
	ruff check --select I $(BACKEND_DIR)
	black $(BACKEND_DIR)

format-ingestion: ## Format ingestion service code
	ruff check --select I $(INGESTION_DIR)
	black $(INGESTION_DIR)

# Testing
test: ## Run backend API tests
	cd $(BACKEND_DIR) && pytest

test-ingestion: ## Run ingestion service tests
	cd $(INGESTION_DIR) && pytest

# Local Development
run-backend: ## Run backend API locally
	cd $(BACKEND_DIR) && uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

run-ingestion: ## Run ingestion service locally
	cd $(INGESTION_DIR) && uvicorn clarivo_ingestion.main:app --reload --host 0.0.0.0 --port 8000

# Docker Commands
docker-build: ## Build all Docker images
	docker-compose build

docker-up: ## Start all services with Docker Compose
	docker-compose up -d

docker-up-logs: ## Start all services and show logs
	docker-compose up

docker-down: ## Stop all services
	docker-compose down

docker-down-volumes: ## Stop all services and remove volumes
	docker-compose down -v

docker-logs: ## Show logs from all services
	docker-compose logs -f

docker-logs-backend: ## Show logs from backend API
	docker-compose logs -f backend-api

docker-logs-ingestion: ## Show logs from ingestion service
	docker-compose logs -f ingestion-service

docker-logs-postgres: ## Show logs from PostgreSQL
	docker-compose logs -f postgres

docker-restart: ## Restart all services
	docker-compose restart

docker-restart-backend: ## Restart backend API service
	docker-compose restart backend-api

docker-restart-ingestion: ## Restart ingestion service
	docker-compose restart ingestion-service

docker-clean: ## Remove all containers, networks, and images
	docker-compose down -v --rmi all

docker-ps: ## Show running containers
	docker-compose ps

docker-exec-backend: ## Execute shell in backend API container
	docker-compose exec backend-api /bin/bash

docker-exec-ingestion: ## Execute shell in ingestion service container
	docker-compose exec ingestion-service /bin/bash

docker-exec-postgres: ## Execute psql in PostgreSQL container
	docker-compose exec postgres psql -U postgres -d orbit

# Database Migrations
migrate: ## Run database migrations
	docker-compose exec backend-api alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MESSAGE="migration message")
	docker-compose exec backend-api alembic revision --autogenerate -m "$(MESSAGE)"

migrate-history: ## Show migration history
	docker-compose exec backend-api alembic history

# Quick Start
start: docker-up ## Start all services (alias for docker-up)
	@echo "Services started! Backend API: http://localhost:8001, Ingestion: http://localhost:8000"

stop: docker-down ## Stop all services (alias for docker-down)
	@echo "Services stopped!"

