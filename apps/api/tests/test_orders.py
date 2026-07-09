from typing import cast

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from apps.accounts.factories import UserFactory
from apps.cart.factories import CartFactory, CartItemFactory
from apps.cart.models import CartItem
from apps.orders.factories import OrderFactory
from apps.orders.models import Order
from apps.payments.models import PaymentMethod
from apps.products.factories import ProductFactory

# =============================================================================
# UNAUTHENTICATED SCENARIO
# =============================================================================


@pytest.mark.django_db
def test_get_orders_unauthenticated(api_client: APIClient) -> None:
    url = reverse("api:orders-list")
    res = cast(Response, api_client.get(url))
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# AUTHENTICATED SCENARIOS
# =============================================================================


@pytest.mark.django_db
def test_get_orders_authenticated_empty(auth_client: APIClient) -> None:
    url = reverse("api:orders-list")
    res = cast(Response, auth_client.get(url))
    assert res.status_code == status.HTTP_200_OK
    assert len(res.data) == 0  # type: ignore


@pytest.mark.django_db
def test_create_order_success(auth_client: APIClient) -> None:
    user = auth_client.user  # type: ignore
    product = ProductFactory(price=10.00, stock=5)

    # Populate DB cart
    cart = CartFactory(user=user)
    CartItemFactory(cart=cart, product=product, quantity=2)

    payment_method, _ = PaymentMethod.objects.get_or_create(
        code="cod", defaults={"name": "Cash on Delivery", "is_active": True}
    )

    url = reverse("api:orders-list")
    data = {
        "shipping_address": "123 Main St, Kyiv",
        "payment_method": payment_method.pk,
    }

    res = cast(Response, auth_client.post(url, data, format="json"))
    assert res.status_code == status.HTTP_201_CREATED
    assert res.data["shipping_address"] == "123 Main St, Kyiv"  # type: ignore
    assert float(res.data["total_price"]) == 20.00  # type: ignore
    assert res.data["status"] == "pending"  # type: ignore
    assert len(res.data["items"]) == 1  # type: ignore

    # Verify cart got cleared
    assert CartItem.objects.filter(cart=cart).exists() is False


@pytest.mark.django_db
def test_create_order_empty_cart(auth_client: APIClient) -> None:
    payment_method, _ = PaymentMethod.objects.get_or_create(
        code="cod", defaults={"name": "Cash on Delivery", "is_active": True}
    )

    url = reverse("api:orders-list")
    data = {
        "shipping_address": "123 Main St, Kyiv",
        "payment_method": payment_method.pk,
    }

    res = cast(Response, auth_client.post(url, data, format="json"))
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "cart" in res.data or "detail" in res.data  # type: ignore


@pytest.mark.django_db
def test_get_order_detail_owner(auth_client: APIClient) -> None:
    user = auth_client.user  # type: ignore
    order = OrderFactory(user=user, total_price=100.00)

    url = reverse("api:orders-detail", kwargs={"uuid": str(order.uuid)})
    res = cast(Response, auth_client.get(url))
    assert res.status_code == status.HTTP_200_OK
    assert res.data["uuid"] == str(order.uuid)  # type: ignore


@pytest.mark.django_db
def test_get_order_detail_non_owner(auth_client: APIClient) -> None:
    other_user = UserFactory()
    order = OrderFactory(user=other_user, total_price=100.00)

    url = reverse("api:orders-detail", kwargs={"uuid": str(order.uuid)})
    res = cast(Response, auth_client.get(url))
    # Expect 404 Not Found to prevent existence leaks
    assert res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_cancel_order_via_delete(auth_client: APIClient) -> None:
    user = auth_client.user  # type: ignore
    order = OrderFactory(user=user, status=Order.Status.PENDING, total_price=50.00)

    url = reverse("api:orders-detail", kwargs={"uuid": str(order.uuid)})
    res = cast(Response, auth_client.delete(url))
    assert res.status_code == status.HTTP_204_NO_CONTENT

    # Verify status changed to cancelled in DB
    order.refresh_from_db()
    assert order.status == Order.Status.CANCELLED


@pytest.mark.django_db
def test_update_status_invalid_fails(auth_client: APIClient) -> None:
    user = auth_client.user  # type: ignore
    order = OrderFactory(user=user, status=Order.Status.PENDING, total_price=50.00)

    url = reverse("api:orders-detail", kwargs={"uuid": str(order.uuid)})
    data = {"status": "shipped"}

    res = cast(Response, auth_client.put(url, data, format="json"))
    assert res.status_code == status.HTTP_400_BAD_REQUEST

    # Allowing only "cancelled" status update
    data_cancelled = {"status": "cancelled"}
    res_cancelled = cast(Response, auth_client.put(url, data_cancelled, format="json"))
    assert res_cancelled.status_code == status.HTTP_200_OK

    order.refresh_from_db()
    assert order.status == Order.Status.CANCELLED


@pytest.mark.django_db
def test_cancel_shipped_order_fails(auth_client: APIClient) -> None:
    user = auth_client.user  # type: ignore
    order = OrderFactory(user=user, status=Order.Status.SHIPPED, total_price=50.00)

    url = reverse("api:orders-detail", kwargs={"uuid": str(order.uuid)})

    # 1. DELETE cancel attempt should fail
    res_delete = cast(Response, auth_client.delete(url))
    assert res_delete.status_code == status.HTTP_400_BAD_REQUEST

    # 2. PUT cancel attempt should fail
    data_cancelled = {"status": "cancelled"}
    res_put = cast(Response, auth_client.put(url, data_cancelled, format="json"))
    assert res_put.status_code == status.HTTP_400_BAD_REQUEST

    # Verify status remains SHIPPED
    order.refresh_from_db()
    assert order.status == Order.Status.SHIPPED
