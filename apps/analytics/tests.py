import json
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.orders.factories import OrderFactory, OrderItemFactory
from apps.orders.models import Order
from apps.products.factories import ProductFactory

pytestmark = pytest.mark.django_db


def test_graphql_endpoint_requires_staff_user(client) -> None:
    """Verify that anonymous and regular users are denied access to the GraphQL API."""
    url = reverse("graphql")
    query = "{ ordersAnalytics { totalOrders } }"

    # 1. Anonymous user
    response = client.post(
        url,
        data=json.dumps({"query": query}),
        content_type="application/json",
    )
    assert response.status_code == 403

    # 2. Authenticated non-staff user
    user = UserFactory(is_staff=False)
    client.force_login(user)
    response = client.post(
        url,
        data=json.dumps({"query": query}),
        content_type="application/json",
    )
    assert response.status_code == 403


def test_graphql_analytics_queries_success(client) -> None:
    """Verify staff user can query full analytics successfully and results are accurate."""
    url = reverse("graphql")
    staff_user = UserFactory(is_staff=True)
    client.force_login(staff_user)

    # Seed data
    buyer1 = UserFactory(email="buyer1@example.com")
    buyer2 = UserFactory(email="buyer2@example.com")

    product_a = ProductFactory(name="Beer A", stock=15, price=10.00)
    product_b = ProductFactory(name="Beer B", stock=5, price=20.00)

    # Paid Order 1 (Buyer 1)
    order1 = OrderFactory(user=buyer1, total_price=30.00, status=Order.Status.PAID)
    OrderItemFactory(order=order1, product=product_a, quantity=3, price=10.00)

    # Paid Order 2 (Buyer 1 - repeat purchaser)
    order2 = OrderFactory(user=buyer1, total_price=20.00, status=Order.Status.PAID)
    OrderItemFactory(order=order2, product=product_b, quantity=1, price=20.00)

    # Paid Order 3 (Buyer 2)
    order3 = OrderFactory(user=buyer2, total_price=10.00, status=Order.Status.PAID)
    OrderItemFactory(order=order3, product=product_a, quantity=1, price=10.00)

    # Unpaid Order (should be excluded from metrics)
    order_unpaid = OrderFactory(user=buyer2, total_price=100.00, status=Order.Status.PENDING)
    OrderItemFactory(order=order_unpaid, product=product_a, quantity=10, price=10.00)

    query = """
    query GetAnalytics {
      ordersAnalytics {
        revenue
        totalOrders
        averageOrderValue
        trends {
          revenue
          count
        }
      }
      productsAnalytics(popularLimit: 2) {
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
    """

    response = client.post(
        url,
        data=json.dumps({"query": query}),
        content_type="application/json",
    )
    assert response.status_code == 200

    data = response.json()
    assert "errors" not in data

    # Verify orders analytics
    orders_data = data["data"]["ordersAnalytics"]
    assert Decimal(orders_data["revenue"]) == Decimal("60.00")  # 30 + 20 + 10
    assert orders_data["totalOrders"] == 3
    assert Decimal(orders_data["averageOrderValue"]) == Decimal("20.00")  # 60 / 3

    # Verify products analytics
    products_data = data["data"]["productsAnalytics"]
    popular = products_data["popularProducts"]
    assert len(popular) == 2
    # Product A should be first (units sold = 4, revenue = 40)
    assert popular[0]["name"] == "Beer A"
    assert popular[0]["unitsSold"] == 4
    assert float(popular[0]["revenue"]) == 40.00

    # Stock levels: sorted by stock ASC; assert both entries explicitly
    # to guard against factory ordering.
    stock = products_data["stockLevels"]
    stock_sorted = sorted(stock, key=lambda s: s["stock"])
    assert stock_sorted[0]["name"] == "Beer B"
    assert stock_sorted[0]["stock"] == 5
    assert stock_sorted[1]["name"] == "Beer A"
    assert stock_sorted[1]["stock"] == 15

    # Verify users analytics
    users_data = data["data"]["usersAnalytics"]
    assert users_data["activeUsersCount"] == 2  # buyer1 and buyer2
    assert users_data["repeatPurchaseRate"] == 50.0  # 1 repeat buyer out of 2 total buyers (50%)
