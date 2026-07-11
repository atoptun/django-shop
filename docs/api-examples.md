# API Usage Examples

This document covers authentication and key endpoint examples for the **REST API** and the **GraphQL analytics API**.

All examples use `curl`. Replace `http://localhost:8010` with your actual host.

---

## REST API

### Base URL

```text
http://localhost:8010/api/
```

The interactive API schema (Swagger UI) is available at:

```text
http://localhost:8010/api/docs/
```

---

### Authentication (JWT)

The REST API uses JWT Bearer tokens. Obtain a token pair with your credentials, then pass the access token in the `Authorization` header for protected endpoints.

#### Register

```bash
curl -X POST http://localhost:8010/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "jane",
    "email": "jane@example.com",
    "password": "securepassword123"
  }'
```

#### Obtain tokens

```bash
curl -X POST http://localhost:8010/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "jane@example.com", "password": "securepassword123"}'
```

```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Refresh an access token

```bash
curl -X POST http://localhost:8010/api/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh_token>"}'
```

> [!NOTE]
> **Access tokens** expire after 60 minutes in production and 7 days in development.
> **Refresh tokens** are valid for 7 days.

---

### User Account

#### Get current user profile *(authenticated)*

```bash
curl http://localhost:8010/api/auth/me/ \
  -H "Authorization: Bearer <access_token>"
```

---

### Products

#### List products

```bash
curl http://localhost:8010/api/products/
```

#### Filter and search

```bash
# Search by name
curl "http://localhost:8010/api/products/?search=unm"

# Filter by category
curl "http://localhost:8010/api/products/?category=adjuncts"

# Order by price descending
curl "http://localhost:8010/api/products/?ordering=price_desc"
```

#### Get a single product

```bash
curl http://localhost:8010/api/products/<slug>/

# Example
curl http://localhost:8010/api/products/saaz-hops/
```

---

### Reviews

#### List product reviews

```bash
curl http://localhost:8010/api/products/<slug>/reviews/

# Example
curl http://localhost:8010/api/products/centennial-hops/reviews/
```

#### Submit a review *(authenticated)*

```bash
curl -X POST http://localhost:8010/api/products/<slug>/reviews/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"rating": 5, "comment": "Excellent hop aroma!"}'
```

---

### Cart

Authenticated users have a persistent cart stored in the database.
*Unauthenticated users **do not have access** to the cart endpoints*
Cart for unauthenticated users **MUST BE** implemented on the frontend.

#### View cart

```bash
curl http://localhost:8010/api/cart/ \
  -H "Authorization: Bearer <access_token>"
```

#### Add item to cart

```bash
curl -X POST http://localhost:8010/api/cart/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"product_slug": "centennial-hops", "quantity": 2}'
```

#### Update item quantity

```bash
curl -X PATCH http://localhost:8010/api/cart/centennial-hops/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"quantity": 3}'
```

#### Remove item

```bash
curl -X DELETE http://localhost:8010/api/cart/centennial-hops/ \
  -H "Authorization: Bearer <access_token>"
```

---

### Orders

Only authenticated users have access to order endpoints.
The order is created from the current cart contents.

#### Place an order

```bash
curl -X POST http://localhost:8010/api/orders/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "shipping_address": "221B Baker Street, London"
  }'
```

#### List my orders

```bash
curl http://localhost:8010/api/orders/ \
  -H "Authorization: Bearer <access_token>"
```

#### Cancel an order

```bash
curl -X DELETE http://localhost:8010/api/orders/<uuid>/ \
  -H "Authorization: Bearer <access_token>"
```

---

### Payments

#### List available payment methods *(public)*

```bash
curl http://localhost:8010/api/payments/methods/
```

#### Pay for an order *(authenticated)*

```bash
# Card payment
curl -X POST http://localhost:8010/api/orders/<uuid>/pay/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_method_code": "debit",
    "payment_data": {
      "card_number": "4000 0000 0000 0002",
      "cvv": "123"
    }
  }'
```

```json
{
  "status": "success",
  "payment_status": "completed",
  "transaction_id": "txn_abc123"
}
```

```bash
# Cash on delivery
curl -X POST http://localhost:8010/api/orders/<uuid>/pay/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"payment_method_code": "cod"}'
```

#### Payment response status codes

| Code | Meaning |
| ------ | --------- |
| `200` | Payment completed successfully |
| `202` | Payment accepted, processing in progress (e.g. bank transfer) |
| `400` | Bad request — order already paid or invalid method |
| `402` | Payment declined by provider |
| `409` | Conflict — another payment is already being processed |

---

## GraphQL Analytics API

### Endpoint

> [!IMPORTANT]
> This endpoint is **staff-only**. You must pass a valid JWT access token or active session belonging to a staff user (`is_staff=True`).

> [!NOTE]
> The GraphiQL interactive explorer is available at `http://localhost:8010/graphql/` in the browser when `DEBUG=True`.

```bash
# Endpoint
POST http://localhost:8010/graphql/
```

#### Authentication

```bash
# 1. Obtain a token for a staff user
curl -X POST http://localhost:8010/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "rootroot"}'

# 2. Use the access token in all GraphQL requests
export TOKEN="<access_token>"
```

#### Query: Order Analytics

```bash
curl -X POST http://localhost:8010/graphql/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ ordersAnalytics { revenue totalOrders averageOrderValue trends { date revenue count } } }"
  }'
```

```json
{
  "data": {
    "ordersAnalytics": {
      "revenue": "1250.00",
      "totalOrders": 42,
      "averageOrderValue": "29.76",
      "trends": [
        { "date": "2026-07-01", "revenue": "340.00", "count": 11 },
        { "date": "2026-07-02", "revenue": "910.00", "count": 31 }
      ]
    }
  }
}
```

#### Query: Product Analytics

```bash
curl -X POST http://localhost:8010/graphql/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ productsAnalytics(popularLimit: 3) { popularProducts { name unitsSold revenue } stockLevels { name stock } } }"
  }'
```

```json
{
  "data": {
    "productsAnalytics": {
      "popularProducts": [
        { "name": "Hop Burst IPA", "unitsSold": 84, "revenue": "840.00" },
        { "name": "Dark Stout",    "unitsSold": 52, "revenue": "624.00" }
      ],
      "stockLevels": [
        { "name": "Seasonal Lager", "stock": 3 },
        { "name": "Dark Stout",     "stock": 12 }
      ]
    }
  }
}
```

#### Query: User Analytics

```bash
curl -X POST http://localhost:8010/graphql/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ usersAnalytics { activeUsersCount repeatPurchaseRate } }"
  }'
```

```json
{
  "data": {
    "usersAnalytics": {
      "activeUsersCount": 38,
      "repeatPurchaseRate": 52.63
    }
  }
}
```

#### Full analytics query (all in one)

```graphql
query GetAnalytics {
  ordersAnalytics {
    revenue
    totalOrders
    averageOrderValue
    trends {
      date
      revenue
      count
    }
  }
  productsAnalytics(popularLimit: 5) {
    popularProducts {
      name
      unitsSold
      revenue
    }
    stockLevels {
      name
      stock
    }
  }
  usersAnalytics {
    activeUsersCount
    repeatPurchaseRate
  }
}
```
