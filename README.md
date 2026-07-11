# Hop & Barley — Django E-Commerce Shop

A full-stack e-commerce web application built with Django 6. Features a storefront with product browsing, a shopping cart, order placement, integrated payment processing, and a staff analytics API backed by GraphQL.

---

## Features

- **Storefront** — product catalog with categories, search, filtering, and product detail pages
- **Shopping cart** — session-based/db-based cart with quantity management
- **Orders** — checkout flow, order history, and cancellation
- **Payments** — pluggable payment providers (card, bank transfer, cash on delivery); declined payments raise typed exceptions surfaced to the user
- **Reviews** — authenticated product reviews with ratings
- **REST API** — full DRF-powered API with JWT authentication and OpenAPI schema (Swagger UI)
- **GraphQL Analytics** — staff-only analytics endpoint (revenue, trends, product popularity, user retention) secured with JWT
- **Admin dashboard** — custom Unfold-based admin with real-time KPIs and period filtering
- **Docker-first** — multi-stage Dockerfile with separate dev (hot-reload, debugpy) and production (Gunicorn + Nginx) targets

---

## Tech Stack

| Layer | Technology |
| --- | --- |
| Framework | Django 6, Django REST Framework |
| API schema | drf-spectacular (OpenAPI 3) |
| GraphQL | graphene-django |
| Auth | djangorestframework-simplejwt |
| Database | PostgreSQL 18 |
| Package manager | [uv](https://github.com/astral-sh/uv) |
| Web server | Gunicorn + Nginx |
| Linting | Ruff, Pyright, djLint |
| Testing | pytest, pytest-django, factory-boy |

---

## Check list

- [X] The project launches with the `docker-compose up` command on a clean system.
- [X] PostgreSQL is used.
- [X] Catalog: filters, search, and pagination are implemented.
- [X] Product page: includes details, reviews, and an "Add to Cart" button.
- [X] Cart: content management is available, total amount is calculated, and stock levels are verified.
- [X] Checkout: order is created, email notification is sent, and data validation is in place.
- [X] Personal account: registration, login, order history, and profile editing are functional.
- [X] Admin panel: features analytics, filters, and convenient data management.
- [X] REST API: JWT authorization is functional, documentation is available, and access permissions are configured.
- [X] GraphQL API: JWT and session authorization is functional, documentation is available, and access permissions are configured.
- [X] Swagger/OpenAPI documentation is available and working correctly.
- [X] Code includes typing and docstrings.
- [X] Linters (ruff) pass without critical errors.
- [X] Tests: 161 items, coverage >= 90%, all passing successfully.
- [X] README is comprehensive and clear.
- [X] Commits are meaningful, branches are used correctly.
- [X] This checklist is added to the project.

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (for local development without Docker)

### 1. Clone and configure

```bash
git clone https://github.com/atoptun/django-shop.git
cd django-shop
cp .env.example .env
```

Edit `.env` and set at minimum:

```dotenv
DJANGO_SECRET_KEY=your-secret-key-here
POSTGRES_PASSWORD=your-db-password
```

> [!WARNING]
> Never use the default `DJANGO_SECRET_KEY` from `.env.example` in production.

### 2. Start the development environment

```bash
make doc-start-dev
```

This builds both the `development` Docker image and starts all services (app, Postgres, Nginx, pgAdmin) with hot-reloading via Docker Compose Watch.

The app will be available at **http://localhost:8010**.

| Service | URL |
|---|---|
| Storefront | http://localhost:8010 |
| Django Admin | http://localhost:8010/admin/ |
| Swagger UI | http://localhost:8010/api/docs/ |
| GraphiQL | http://localhost:8010/graphql/ |
| pgAdmin | http://localhost:8010/pgadmin/ |

Default admin credentials (set in `.env`):

```text
# Django admin
Username: admin
Password: rootroot

# pgAdmin
Email: admin@local.org
Password: rootroot
```

### 3. Stop the environment

```bash
make doc-stop-dev
```

---

## Production Deployment

```bash
make doc-start-prod
```

Builds the `production` Docker image (no dev dependencies, runs as a non-root user) and starts the stack with Gunicorn behind Nginx.

To view logs:

```bash
make doc-logs-prod app
```

---

## Local Development (Docker)

Python debug port is exposed on `localhost:5678`. You can attach a debugger (e.g., VS Code, PyCharm) to the running container.
Also a debug port can be changed in `compose.dev.yml`.

Additional delopment commands (`Makefile`):

```bash
# Install dependencies
uv sync

# Restart container
make doc-restart-dev <service name>

# View logs
make doc-logs-dev <service name>

# Shell into the container
make doc-shell-dev <service name>

# Generate a local migration script
# (context: Postgres container must be running)
make db-migrate

# Apply migrations into the database
# (context: Postgres container must be running)
make db-upgrade
```

Sent email in debug mode is placed `logs/dev/sent_emails`.

Also available Django subcommand (run inside the container `app`):

```bash
# Shell into the container
make doc-shell-dev app

# Create a superuser if it doesn't exist - run automatically on startup container
setup_admin

# Seed the database with fake addresses for a user profile.
uv run manage.py seed_addresses --username <username> --quantity <quantity>


# Seed database with products and categories loaded from local products_data.json file.
uv run manage.py seed_products

# Seeds random reviews using Faker for a specified product.
uv run manage.py seed_reviews <product_identifier> -quantity <quantity> --status <status {pending,approved,rejected}>
```

---

## Local Development (without Docker)

Requires a running Postgres instance on `localhost:5433`.

```bash
# Install dependencies
uv sync

# Apply migrations
make db-upgrade

# Run the dev server
uv run task dev
```

---

## Running Tests

Tests are collected from all `apps/` submodules. A `.env.test` file is loaded automatically.
Postgres container must be running for tests to pass.

```bash
# Run the full test suite with coverage
uv run pytest
```

Coverage reports are written to `htmlcov/` and printed in the terminal after each run.

---

## Linting and Formatting

```bash
# Check everything (Ruff + Pyright)
uv run task lint

# Auto-fix Ruff issues and format
uv run task fix

# Run all pre-commit hooks against staged files
uv run pre-commit
```

Pre-commit hooks run automatically on `git commit` after `pre-commit install`. They cover trailing whitespace, YAML/TOML validation, merge conflict detection, Ruff linting, and djLint template formatting.

---

## Project Structure

```text
django-shop/
├── apps/                    # Django applications
│   ├── accounts/            # Custom user model, registration, profile
│   ├── analytics/           # GraphQL analytics API + services
│   │   └── graphql/         # Schema, types (.pyi stubs), resolvers
│   ├── api/                 # DRF REST API (serializers, views, tests)
│   ├── cart/                # Session-based/DB-based shopping cart
│   ├── dashboard/           # Custom Unfold admin dashboard
│   ├── orders/              # Order model, service, views
│   ├── payments/            # Payment models, providers, service, exceptions
│   ├── products/            # Product & category models, views
│   └── reviews/             # Product reviews
├── core/                    # Project configuration
│   ├── settings.py
│   ├── urls.py
│   └── config.py            # pydantic-settings env config
├── nginx/                   # Nginx configs (dev + prod)
├── templates/               # Django HTML base templates
├── static/                  # Static assets (JS, CSS)
├── docs/                    # Additional documentation
├── compose.yml              # Production Docker Compose config
├── compose.dev.yml          # Dev overrides (hot-reload, debugpy)
├── Dockerfile               # Multi-stage build (development / production)
├── Makefile                 # Developer task shortcuts
└── pyproject.toml           # Dependencies, Ruff, Pyright, pytest config
```

### Key design decisions

- **Payment providers** are pluggable via `PaymentProviderFactory`. Adding a new provider means implementing one class — no changes to the service or views.
- **Typed exceptions** (`PaymentDeclinedError`, `InvalidPaymentMethodError`, etc.) flow from the service layer up through views and the API, mapped to HTTP status codes at the boundary.
- **Two-layer API** — a Django template-based storefront and a DRF REST API share the same models and services. The GraphQL endpoint is a separate read-only analytics layer for staff.
- **Analytics services** (`OrderAnalyticsService`, `ProductAnalyticsService`, `UserAnalyticsService`) are plain Python classes importable by both the GraphQL resolvers and the admin dashboard.

---

## API Examples

Full curl examples for REST and GraphQL are in **[docs/api-examples.md](docs/api-examples.md)**, including JWT authentication, all major endpoints, and sample responses.

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DEBUG` | Django debug mode | `True` |
| `DJANGO_SECRET_KEY` | Secret key | — *(required)* |
| `DJANGO_ALLOWED_HOSTS` | JSON list of allowed hosts | `["localhost", ...]` |
| `DJANGO_SUPERUSER_USERNAME` | Auto-created admin username | `admin` |
| `DJANGO_SUPERUSER_PASSWORD` | Auto-created admin password | `rootroot` |
| `POSTGRES_HOST` | Database host | `postgres` |
| `POSTGRES_PORT` | Database port | `5432` |
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | — *(required)* |
| `POSTGRES_DB` | Database name | `django_shop` |
| `NGINX_OUT_PORT` | Nginx exposed port | `8010` |
| `PGADMIN_EMAIL` | pgAdmin login email | `admin@local.org` |
| `PGADMIN_PASSWORD` | pgAdmin password | `rootroot` |

See [`.env.example`](.env.example) for the full template.
