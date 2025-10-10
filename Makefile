.PHONY: help up down restart build logs ps clean dev test migrate seed ollama-pull

# Colors for output
RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[0;33m
NC=\033[0m # No Color

help: ## Show this help message
	@echo "$(GREEN)LegalEase Docker Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# ============================================
# Docker Compose Commands
# ============================================

up: ## Start all services
	docker compose up -d
	@echo "$(GREEN)All services started!$(NC)"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"

down: ## Stop all services
	docker compose down
	@echo "$(GREEN)All services stopped$(NC)"

down-v: ## Stop all services and remove volumes
	docker compose down -v
	@echo "$(RED)All services stopped and volumes removed$(NC)"

restart: ## Restart all services
	docker compose restart
	@echo "$(GREEN)All services restarted$(NC)"

restart-%: ## Restart specific service (e.g., make restart-backend)
	docker compose restart $*
	@echo "$(GREEN)Service $* restarted$(NC)"

build: ## Build all services
	docker compose build
	@echo "$(GREEN)All services built$(NC)"

build-%: ## Build specific service (e.g., make build-backend)
	docker compose build $*
	@echo "$(GREEN)Service $* built$(NC)"

rebuild: ## Rebuild all services without cache
	docker compose build --no-cache
	@echo "$(GREEN)All services rebuilt$(NC)"

up-build: ## Build and start all services
	docker compose up -d --build
	@echo "$(GREEN)All services built and started$(NC)"

# ============================================
# Service-Specific Commands
# ============================================

up-infra: ## Start only infrastructure services (postgres, redis, etc.)
	docker compose up -d postgres redis qdrant minio neo4j ollama
	@echo "$(GREEN)Infrastructure services started$(NC)"

up-backend: ## Start backend and dependencies
	docker compose up -d backend worker beat
	@echo "$(GREEN)Backend services started$(NC)"

up-frontend: ## Start frontend
	docker compose up -d frontend
	@echo "$(GREEN)Frontend started$(NC)"

# ============================================
# Logs
# ============================================

logs: ## View logs from all services
	docker compose logs -f

logs-%: ## View logs from specific service (e.g., make logs-backend)
	docker compose logs -f $*

logs-tail: ## View last 100 lines of logs
	docker compose logs --tail=100

# ============================================
# Status & Monitoring
# ============================================

ps: ## Show status of all services
	docker compose ps

stats: ## Show resource usage statistics
	docker stats

health: ## Check health status of all services
	@echo "$(YELLOW)Checking service health...$(NC)"
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

# ============================================
# Shell Access
# ============================================

shell-backend: ## Open shell in backend container
	docker compose exec backend bash

shell-frontend: ## Open shell in frontend container
	docker compose exec frontend sh

shell-worker: ## Open shell in worker container
	docker compose exec worker bash

shell-postgres: ## Open PostgreSQL shell
	docker compose exec postgres psql -U legalease -d legalease

shell-redis: ## Open Redis CLI
	docker compose exec redis redis-cli

shell-neo4j: ## Open Neo4j Cypher shell
	docker compose exec neo4j cypher-shell -u neo4j -p legalease_dev

# ============================================
# Database Management
# ============================================

migrate: ## Run database migrations
	docker compose exec backend alembic upgrade head
	@echo "$(GREEN)Migrations applied$(NC)"

migrate-create: ## Create new migration (use name=your_migration_name)
	docker compose exec backend alembic revision --autogenerate -m "$(name)"
	@echo "$(GREEN)Migration created$(NC)"

migrate-down: ## Rollback last migration
	docker compose exec backend alembic downgrade -1
	@echo "$(YELLOW)Migration rolled back$(NC)"

migrate-history: ## Show migration history
	docker compose exec backend alembic history

db-reset: ## Reset database (WARNING: deletes all data)
	@echo "$(RED)This will delete all database data. Are you sure? [y/N]$(NC)" && read ans && [ $${ans:-N} = y ]
	docker compose down
	docker volume rm legalease-postgres-data
	docker compose up -d postgres
	@echo "$(YELLOW)Waiting for PostgreSQL to be ready...$(NC)"
	@sleep 5
	$(MAKE) migrate
	@echo "$(GREEN)Database reset complete$(NC)"

# ============================================
# Testing
# ============================================

test: ## Run backend tests
	docker compose exec backend pytest

test-v: ## Run backend tests with verbose output
	docker compose exec backend pytest -v

test-cov: ## Run backend tests with coverage
	docker compose exec backend pytest --cov=app --cov-report=html

test-frontend: ## Run frontend tests
	docker compose exec frontend pnpm test

# ============================================
# Development
# ============================================

dev: ## Start in development mode with logs
	docker compose up

dev-frontend: ## Start only frontend in development mode
	docker compose up frontend

dev-backend: ## Start only backend in development mode
	docker compose up backend worker

# ============================================
# Ollama Management
# ============================================

ollama-pull: ## Pull all required Ollama models
	@echo "$(YELLOW)Pulling Ollama models (this may take a while)...$(NC)"
	docker compose exec ollama ollama pull llama3.1
	docker compose exec ollama ollama pull nomic-embed-text
	@echo "$(GREEN)Ollama models downloaded$(NC)"

ollama-list: ## List available Ollama models
	docker compose exec ollama ollama list

ollama-pull-%: ## Pull specific Ollama model (e.g., make ollama-pull-llama3.1)
	docker compose exec ollama ollama pull $*

# ============================================
# Seed & Setup
# ============================================

setup: up-infra migrate ollama-pull ## Complete initial setup
	@echo "$(GREEN)Initial setup complete!$(NC)"
	@echo "Run '$(YELLOW)make up$(NC)' to start all services"

seed: ## Seed database with sample data
	docker compose exec backend python -m app.scripts.seed_data
	@echo "$(GREEN)Database seeded$(NC)"

# ============================================
# Cleanup
# ============================================

clean: ## Stop services and remove containers
	docker compose down
	@echo "$(GREEN)Containers removed$(NC)"

clean-all: ## Remove containers, volumes, and images
	docker compose down -v --rmi all
	@echo "$(RED)All containers, volumes, and images removed$(NC)"

prune: ## Remove all unused Docker resources
	docker system prune -af --volumes
	@echo "$(RED)All unused Docker resources removed$(NC)"

# ============================================
# Backup & Restore
# ============================================

backup-db: ## Backup PostgreSQL database
	@mkdir -p backups
	docker compose exec -T postgres pg_dump -U legalease legalease > backups/legalease_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Database backed up to backups/$(NC)"

restore-db: ## Restore PostgreSQL database (use file=backups/filename.sql)
	docker compose exec -T postgres psql -U legalease -d legalease < $(file)
	@echo "$(GREEN)Database restored$(NC)"

# ============================================
# Production
# ============================================

prod-build: ## Build for production
	docker compose -f docker-compose.yml -f docker-compose.prod.yml build

prod-up: ## Start in production mode
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-down: ## Stop production services
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down

# ============================================
# Monitoring
# ============================================

watch: ## Watch service status continuously
	watch -n 2 docker compose ps

tail-all: ## Tail logs from all services
	docker compose logs -f --tail=50
