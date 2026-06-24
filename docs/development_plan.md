# Development Plan: Django Shop

This document outlines the step-by-step development roadmap for the Django/DRF e-commerce application based on the requirements in `task.md` and the design decisions made.

## Phase 1: Database Models & Migrations

1. **App Registration**: Register `apps.accounts`, `apps.products`, `apps.orders`, and `apps.reviews` in `INSTALLED_APPS` within [settings.py](file:///home/topa/study/jr/projects/django-shop/core/settings.py).
2. **Accounts App**:
   - Create `Profile` model in `apps/accounts/models.py` containing `phone`, `city`, and `address` fields, linked via a `OneToOneField` to standard `User`.
   - Setup Django signals to automatically create and update the user's `Profile` when a `User` instance is saved.
3. **Products App**:
   - Create `Category` model with a self-referential `parent` foreign key (supporting nested categories).
   - Create `Product` model containing basic attributes (`name`, `slug`, `description`, `price`, `image`, `stock`, `is_active`) and brewing-specific specification fields (`origin`, `product_type`, `alpha_acids`, `beta_acids`, `aroma_profile`, `usage`, `recommended_styles`).
4. **Reviews App**:
   - Create `Review` model with `product`, `user`, `rating` (1-5), and `comment` fields.
5. **Orders App**:
   - Create `Cart` and `CartItem` models for authenticated users.
   - Create `Order` model with `user`, `status` (`pending`, `paid`, `shipped`, `delivered`, `cancelled`), `total_price`, and shipping details.
   - Create `OrderItem` model referencing `order`, `product`, `quantity`, and a snapshotted `price`.
6. **Migrations**: Generate and apply migrations using `makemigrations` and `migrate`.

## Phase 2: Web Interface (Views & Templates Integration)

1. **URL Routing**: Configure global routing in [urls.py](file:///home/topa/study/jr/projects/django-shop/core/urls.py) and delegate views to respective app-level routing.
2. **Catalog / Products List**:
   - Implement catalog logic supporting pagination, search, sorting (price, rating, newness), and product type filtering.
3. **Product Detail**:
   - Render spec accordions, review history, and a review form (restricted to users who have previously ordered that product).
4. **Cart Management**:
   - Implement cart business logic: read/write Django sessions for anonymous users and synchronize to `Cart` and `CartItem` database models once a user logs in.
5. **Checkout**:
   - Implement validation forms for delivery data, subtract product stock under a database transaction block, clear the cart, and send an email confirmation.
6. **User Account**:
   - Build account dashboard with dynamic order history tracking and profile updating form.
   - Setup session authentication templates for Login, Registration, and Password Reset.

## Phase 3: REST API & JWT Authentication

1. **Authentication Backend**: Configure `djangorestframework-simplejwt` for `/api/users/login/` returning access and refresh tokens.
2. **Serializers**: Create Django REST Framework serializers matching all target schemas.
3. **ViewSets & Routers**:
   - `/api/products/` (including nested `/api/products/<id>/reviews/` endpoints with purchase-validated POST authorization).
   - `/api/orders/` (user-isolated endpoint mapping order logs).
   - `/api/cart/` (stateful REST endpoints accessing authenticated database-backed carts).
   - `/api/users/register/`.

## Phase 4: API Documentation, Testing & Linters

1. **API Documentation**: Configure `drf-spectacular` OpenAPI schema endpoints and serve them at `/api/docs/`.
2. **Unit Tests**:
   - Setup `pytest-django`.
   - Write tests validating database stock limits, checkout order creation, user review permission rules, and JWT auth filters.
3. **Code Quality**: Run static analysis (`ruff`, `pyright`) to verify clean type checking and formatting.
