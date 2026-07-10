from typing import cast

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response

from apps.api.tests import APIClient, AuthClient
from apps.orders.factories import OrderFactory
from apps.orders.models import Order
from apps.payments.factories import PaymentFactory, PaymentMethodFactory
from apps.payments.models import Payment, PaymentMethod


@pytest.mark.django_db
def test_get_payment_methods_success(api_client: APIClient) -> None:
    PaymentMethod.objects.all().delete()
    PaymentMethodFactory(code="debit", name="Card", is_active=True)
    PaymentMethodFactory(code="cod", name="COD", is_active=True)
    PaymentMethodFactory(code="inactive-method", name="Inactive", is_active=False)

    url = reverse("api:payment-methods-list")
    res = cast(Response, api_client.get(url))
    assert res.status_code == status.HTTP_200_OK

    res_data = cast(list, res.data)
    assert len(res_data) == 2
    codes = {m["code"] for m in res_data}
    assert "debit" in codes
    assert "cod" in codes
    assert "inactive-method" not in codes


@pytest.mark.django_db
def test_pay_order_success(auth_client: AuthClient) -> None:
    PaymentMethodFactory(code="debit", name="Card")
    order = OrderFactory(user=auth_client.user, status=Order.Status.PENDING)

    url = reverse("api:orders-pay", kwargs={"uuid": str(order.uuid)})
    data = {
        "payment_method_code": "debit",
        "payment_data": {"card_number": "4000 0000 0000 0002", "cvv": "123"},
    }

    res = cast(Response, auth_client.post(url, data, format="json"))
    assert res.status_code == status.HTTP_200_OK

    res_data = cast(dict, res.data)
    assert res_data["status"] == "success"
    assert res_data["payment_status"] == Payment.Status.COMPLETED
    assert "transaction_id" in res_data

    order.refresh_from_db()
    assert order.status == Order.Status.PAID


@pytest.mark.django_db
def test_pay_order_declined(auth_client: AuthClient) -> None:
    PaymentMethodFactory(code="debit", name="Card")
    order = OrderFactory(user=auth_client.user, status=Order.Status.PENDING)

    url = reverse("api:orders-pay", kwargs={"uuid": str(order.uuid)})
    data = {
        "payment_method_code": "debit",
        "payment_data": {"card_number": "4000 0000 0000 0005", "cvv": "000"},
    }

    res = cast(Response, auth_client.post(url, data, format="json"))
    assert res.status_code == status.HTTP_402_PAYMENT_REQUIRED
    assert "Card Insufficient Funds" in str(res.data["detail"])


@pytest.mark.django_db
def test_pay_order_invalid_method(auth_client: AuthClient) -> None:
    order = OrderFactory(user=auth_client.user, status=Order.Status.PENDING)

    url = reverse("api:orders-pay", kwargs={"uuid": str(order.uuid)})
    data = {
        "payment_method_code": "invalid_code",
    }

    res = cast(Response, auth_client.post(url, data, format="json"))
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "Payment method is invalid or inactive." in str(res.data["detail"])


@pytest.mark.django_db
def test_pay_order_already_paid(auth_client: AuthClient) -> None:
    PaymentMethodFactory(code="debit", name="Card")
    order = OrderFactory(user=auth_client.user, status=Order.Status.PAID)

    url = reverse("api:orders-pay", kwargs={"uuid": str(order.uuid)})
    data = {
        "payment_method_code": "debit",
        "payment_data": {"card_number": "4000 0000 0000 0002", "cvv": "123"},
    }

    res = cast(Response, auth_client.post(url, data, format="json"))
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "This order has already been paid." in str(res.data["detail"])


@pytest.mark.django_db
def test_pay_order_processing_conflict(auth_client: AuthClient) -> None:
    method = PaymentMethodFactory(code="bank", name="Bank")
    order = OrderFactory(user=auth_client.user, status=Order.Status.PENDING)
    PaymentFactory(order=order, payment_method=method, status=Payment.Status.PROCESSING)

    url = reverse("api:orders-pay", kwargs={"uuid": str(order.uuid)})
    data = {
        "payment_method_code": "bank",
    }

    res = cast(Response, auth_client.post(url, data, format="json"))
    assert res.status_code == status.HTTP_409_CONFLICT
    assert "Payment is already being processed." in str(res.data["detail"])
