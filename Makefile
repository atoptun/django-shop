# Load environment variables from .env file if it exists
ifneq ($(wildcard .env),)
    include .env
    export
endif

# Default local network settings (for running migrations directly on host machine)
LOCAL_DB_HOST=127.0.0.1
LOCAL_DB_PORT=5433
DOCKER_DEV_PROJECT_NAME=dj_shop_dev
DOCKER_PROD_PROJECT_NAME=dj_shop_prod

.PHONY: help db-migrate db-upgrade db-seed-test-source doc-migrate doc-upgrade doc-current doc-history

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# =============================================================================
# DEVELOPMENT ENVIRONMENT
# =============================================================================

doc-start-dev: ## Start the development environment with hot-reloading
	docker compose -p $(DOCKER_DEV_PROJECT_NAME) --env-file .env -f compose.yml -f compose.dev.yml up --build --watch

doc-stop-dev: ## Stop the development environment
	docker compose -p $(DOCKER_DEV_PROJECT_NAME) --env-file .env -f compose.yml -f compose.dev.yml down --remove-orphans

doc-restart-dev: ## Restart container (Usage: make doc-restart-dev api)
	@# Filter out the command name itself, leaving only the container name
	$(eval CONTAINER := $(filter-out doc-restart-dev,$(MAKECMDGOALS)))
	@# If no container was provided, default to 'api'
	$(eval CONTAINER_NAME := $(if $(CONTAINER),$(CONTAINER),api))
	docker compose -p $(DOCKER_DEV_PROJECT_NAME) restart  $(CONTAINER_NAME)

doc-logs-dev: ## View container logs (Usage: make doc-logs-dev api)
	@# Filter out the command name itself, leaving only the container name
	$(eval CONTAINER := $(filter-out doc-logs-dev,$(MAKECMDGOALS)))
	@# If no container was provided, default to 'api'
	$(eval CONTAINER_NAME := $(if $(CONTAINER),$(CONTAINER),api))
	docker compose -p $(DOCKER_DEV_PROJECT_NAME) logs -f $(CONTAINER_NAME)

# =============================================================================
# PRODUCTION ENVIRONMENT
# =============================================================================

doc-start-prod: ## Start the production environment
	docker compose -p $(DOCKER_PROD_PROJECT_NAME) --env-file .env -f compose.yml up -d --build

doc-stop-prod: ## Stop the production environment
	docker compose -p $(DOCKER_PROD_PROJECT_NAME) --env-file .env -f compose.yml down

doc-logs-prod: ## View container logs (Usage: make doc-logs-prod api)
	@# Filter out the command name itself, leaving only the container name
	$(eval CONTAINER := $(filter-out doc-logs-prod,$(MAKECMDGOALS)))
	@# If no container was provided, default to 'api'
	$(eval CONTAINER_NAME := $(if $(CONTAINER),$(CONTAINER),api))
	docker compose -p $(DOCKER_PROD_PROJECT_NAME) logs -f $(CONTAINER_NAME)


# =============================================================================
# LOCAL MIGRATIONS (Using 'uv' directly on the host machine)
# =============================================================================

db-migrate: ## Generate a local migration script (Usage: make db-migrate m="migration description")
	@if [ -z "$(m)" ]; then echo "Error: Please specify a migration message. Example: make db-migrate m='init tables'"; exit 1; fi
	POSTGRES_HOST=$(LOCAL_DB_HOST) POSTGRES_PORT=$(LOCAL_DB_PORT) uv run manage.py makemigrations

db-upgrade: ## Apply all pending migrations to the local database
	POSTGRES_HOST=$(LOCAL_DB_HOST) POSTGRES_PORT=$(LOCAL_DB_PORT) uv run manage.py migrate

db-seed-test-source: ## Seed a stable enabled site source into the local database
	POSTGRES_HOST=$(LOCAL_DB_HOST) POSTGRES_PORT=$(LOCAL_DB_PORT) uv run python -m app.seed

db-current: ## Display the current migration revision of the Docker database
	POSTGRES_HOST=$(LOCAL_DB_HOST) POSTGRES_PORT=$(LOCAL_DB_PORT) uv run manage.py showmigrations
db-history: ## List the full migration history from the Docker container context
	POSTGRES_HOST=$(LOCAL_DB_HOST) POSTGRES_PORT=$(LOCAL_DB_PORT) uv run manage.py showmigrations --plan

# =============================================================================
# DOCKER MIGRATIONS (Executed inside the running 'api' container)
# =============================================================================

doc-migrate: ## Generate a migration script INSIDE Docker container (Usage: make doc-migrate m="description")
	@if [ -z "$(m)" ]; then echo "Error: Please specify a migration message. Example: make doc-migrate m='init tables'"; exit 1; fi
	docker compose -p $(DOCKER_DEV_PROJECT_NAME) exec app uv run alembic revision --autogenerate -m "$(m)"

doc-upgrade: ## Apply all pending migrations INSIDE Docker container
	docker compose -p $(DOCKER_DEV_PROJECT_NAME) exec app uv run alembic upgrade head

doc-current: ## Display the current migration revision of the Docker database
	docker compose -p $(DOCKER_DEV_PROJECT_NAME) exec app uv run alembic current

doc-history: ## List the full migration history from the Docker container context
	docker compose -p $(DOCKER_DEV_PROJECT_NAME) exec app uv run alembic history -v


# This catch-all rule prevents Make from failing if you pass extra words
%:
	@:	