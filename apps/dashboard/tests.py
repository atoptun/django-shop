import pytest
from django.test import RequestFactory
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.dashboard.dashboard import get_dashboard_context
from apps.orders.factories import OrderFactory
from apps.orders.models import Order

pytestmark = pytest.mark.django_db


def test_dashboard_context_day_period() -> None:
    rf = RequestFactory()
    request = rf.get("/admin/", {"period": "day"})

    # Create active users
    UserFactory(is_active=True)
    UserFactory(is_active=True)

    # Create orders with different statuses
    OrderFactory(total_price=100.0, status=Order.Status.PAID)
    OrderFactory(total_price=50.0, status=Order.Status.PENDING)
    OrderFactory(total_price=200.0, status=Order.Status.CANCELLED)

    context = get_dashboard_context(request, {})

    assert context["total_sales"] == 100.0
    assert context["total_orders"] == 3
    assert context["total_pending"] == 1
    assert context["current_period"] == "day"


def test_admin_dashboard_view_unauthenticated(client) -> None:
    url = reverse("admin_dashboard")
    response = client.get(url)
    # Unauthenticated users should be redirected to login
    assert response.status_code == 302
    assert "login" in response.url


def test_admin_dashboard_view_authenticated(client) -> None:
    admin_user = UserFactory(is_staff=True, is_superuser=True)
    client.force_login(admin_user)

    url = reverse("admin_dashboard")
    response = client.get(url)

    assert response.status_code == 200
    assert "total_sales" in response.context
    assert "total_users" in response.context
