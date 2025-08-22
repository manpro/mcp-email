.PHONY: help up down logs migrate seed refresh test clean reset

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	docker-compose up -d --build

down: ## Stop all services
	docker-compose down

clean: ## Stop all services and remove volumes
	docker-compose down -v

logs: ## Show logs for all services
	docker-compose logs -f --tail 200

migrate: ## Run database migrations
	docker-compose run --rm backend alembic upgrade head

seed: ## Seed initial data
	docker-compose exec backend python -m app.utils seed

refresh: ## Trigger manual refresh
	curl -X POST http://localhost:8000/refresh

test: ## Run backend tests
	docker-compose run --rm backend pytest

reset: clean up migrate seed ## Reset everything and start fresh
	@echo "System reset complete"

shell-backend: ## Open backend shell
	docker-compose exec backend /bin/bash

shell-db: ## Open database shell
	docker-compose exec postgres psql -U rss rssintel

status: ## Check service status
	@echo "Service Status:"
	@docker-compose ps
	@echo "\nHealth Checks:"
	@curl -s http://localhost:8000/health | jq '.' || echo "Backend not responding"
	@curl -s http://localhost:8081 > /dev/null && echo "FreshRSS: OK" || echo "FreshRSS: Failed"
	@curl -s http://localhost:1200 > /dev/null && echo "RSSHub: OK" || echo "RSSHub: Failed"
	@curl -s http://localhost:3001 > /dev/null && echo "Web UI: OK" || echo "Web UI: Failed"