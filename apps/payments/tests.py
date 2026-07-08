import json

import pytest
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.orders.factories import OrderFactory
from apps.orders.models import Order
from apps.payments.factories import PaymentFactory, PaymentMethodFactory
from apps.payments.models import Payment
from apps.payments.services import PaymentService

User = get_user_model()
pytestmark = pytest.mark.django_db


def test_payment_model_relations():
    """Verify payment model string conversion, choices, and defaults."""
    method = PaymentMethodFactory(code="test_pm", name="Test Pay")
    order = OrderFactory()
    payment = PaymentFactory(
        order=order,
        payment_method=method,
        transaction_id="txn_test",
        status=Payment.Status.PENDING,
    )

    assert payment.order == order
    assert payment.payment_method == method
    assert payment.transaction_id == "txn_test"
    assert payment.status == Payment.Status.PENDING
    assert str(payment) == f"Payment for Order #{order.pk} via Test Pay (pending)"


def test_payment_service_successful_charge():
    """Verify that a successful card charge transits order status to PAID."""
    method = PaymentMethodFactory(code="debit", name="Stripe Card")
    order = OrderFactory(status=Order.Status.PENDING)

    # Simulate a successful Stripe card charge
    result = PaymentService.process_order_payment(
        order, method, {"card_number": "4000 0000 0000 0002", "cvv": "123"}
    )

    assert result["success"] is True
    assert result["status"] == Payment.Status.COMPLETED
    assert result["transaction_id"] is not None

    # Reload model
    order.refresh_from_db()
    payment = order.payment
    assert payment.status == Payment.Status.COMPLETED
    assert order.status == Order.Status.PAID


def test_payment_service_failed_charge():
    """Verify that a declined card charge leaves the order as PENDING
    and marks payment as FAILED.
    """
    method = PaymentMethodFactory(code="debit", name="Stripe Card")
    order = OrderFactory(status=Order.Status.PENDING)

    # Simulate a declined Stripe card charge
    result = PaymentService.process_order_payment(
        order, method, {"card_number": "4000 0000 0000 0005", "cvv": "000"}
    )

    assert result["success"] is False
    assert result["status"] == Payment.Status.FAILED
    assert "Card Insufficient Funds" in result["error"]

    order.refresh_from_db()
    payment = order.payment
    assert payment.status == Payment.Status.FAILED
    assert order.status == Order.Status.PENDING


def test_cash_on_delivery_processing():
    """Verify Cash On Delivery checkout keeps order and payment PENDING."""
    method = PaymentMethodFactory(code="cod", name="Cash On Delivery")
    order = OrderFactory(status=Order.Status.PENDING)

    result = PaymentService.process_order_payment(order, method, {})

    assert result["success"] is True
    assert result["status"] == Payment.Status.PENDING

    order.refresh_from_db()
    payment = order.payment
    assert payment.status == Payment.Status.PENDING
    assert order.status == Order.Status.PENDING


def test_failed_then_success_payment_retry_flow(client):
    """Verify failed-then-success retry flow via the payment view page."""
    user = UserFactory()
    client.force_login(user)

    method = PaymentMethodFactory(code="debit", name="Stripe Card")
    order = OrderFactory(user=user, status=Order.Status.PENDING)
    payment = PaymentFactory(order=order, payment_method=method, status=Payment.Status.PENDING)

    url = reverse("payments:pay", kwargs={"order_uuid": order.uuid})

    # Step 1: Submit failed payment credentials
    response = client.post(
        url, {"payment_method": method.id, "card_number": "4000 0000 0000 0005", "cvv": "000"}
    )

    assert response.status_code == 200
    from django.contrib.messages import get_messages

    messages = [str(m) for m in get_messages(response.wsgi_request)]
    assert any("Payment Failed" in msg for msg in messages)

    order.refresh_from_db()
    payment.refresh_from_db()
    assert payment.status == Payment.Status.FAILED
    assert order.status == Order.Status.PENDING

    # Step 2: Retry with successful card details on the same order
    response = client.post(
        url, {"payment_method": method.id, "card_number": "4000 0000 0000 0002", "cvv": "123"}
    )

    assert response.status_code == 302
    assert response.url == reverse("accounts:order_history")

    order.refresh_from_db()
    payment.refresh_from_db()
    assert payment.status == Payment.Status.COMPLETED
    assert order.status == Order.Status.PAID


def test_stripe_and_paypal_webhook_receivers(client):
    """Verify that Stripe and PayPal webhooks successfully update order status."""
    method = PaymentMethodFactory(code="debit", name="Stripe Card")
    order = OrderFactory(status=Order.Status.PENDING)
    payment = PaymentFactory(
        order=order,
        payment_method=method,
        transaction_id="txn_stripe_webhook_123",
        status=Payment.Status.PROCESSING,
    )

    webhook_url = reverse("payments:webhook", kwargs={"provider_name": "stripe"})

    # Call Stripe webhook
    payload = {
        "transaction_id": "txn_stripe_webhook_123",
        "status": "completed",
        "event": "checkout.session.completed",
    }
    response = client.post(webhook_url, json.dumps(payload), content_type="application/json")

    assert response.status_code == 200
    order.refresh_from_db()
    payment.refresh_from_db()
    assert payment.status == Payment.Status.COMPLETED
    assert order.status == Order.Status.PAID


def test_soft_deletion_annotation_safety():
    """Verify database count annotations ignore soft-deleted payment logs."""
    user = UserFactory()

    method = PaymentMethodFactory(code="debit")

    o1 = OrderFactory(user=user)
    o2 = OrderFactory(user=user)
    o3 = OrderFactory(user=user)

    PaymentFactory(order=o1, payment_method=method, status=Payment.Status.COMPLETED)
    PaymentFactory(order=o2, payment_method=method, status=Payment.Status.COMPLETED)
    p3 = PaymentFactory(order=o3, payment_method=method, status=Payment.Status.COMPLETED)

    # Soft delete p3
    p3.delete()

    # Run annotation query
    annotated_user = User.objects.annotate(
        payment_count=Count("orders__payment", filter=Q(orders__payment__deleted__isnull=True)),
        total_spent=Sum(
            "orders__payment__order__total_price", filter=Q(orders__payment__deleted__isnull=True)
        ),
    ).get(id=user.id)

    # Check that soft-deleted payment is ignored
    assert annotated_user.payment_count == 2
    assert annotated_user.total_spent == float(o1.total_price + o2.total_price)


def test_auto_confirm_cod_payment_signal():
    """Verify that updating an order's status to DELIVERED auto-completes COD payments."""
    method = PaymentMethodFactory(code="cod", name="Cash On Delivery")
    order = OrderFactory(status=Order.Status.SHIPPED)
    payment = PaymentFactory(order=order, payment_method=method, status=Payment.Status.PENDING)

    # Change order status to DELIVERED
    order.status = Order.Status.DELIVERED
    order.save()

    payment.refresh_from_db()
    assert payment.status == Payment.Status.COMPLETED


def test_unsupported_provider_factory_exception():
    """Verify that requesting an unsupported provider code raises PaymentProviderNotFound."""
    from apps.payments.providers import PaymentProviderFactory, PaymentProviderNotFound

    with pytest.raises(PaymentProviderNotFound) as exc_info:
        PaymentProviderFactory.get_simulator("unsupported_gateway")
    assert "not supported" in str(exc_info.value)


def test_unsupported_provider_webhook_response(client):
    """Verify that posting a webhook to an unsupported provider yields HTTP 400."""
    url = reverse("payments:webhook", kwargs={"provider_name": "unknown_provider"})
    payload = {"transaction_id": "txn_123", "status": "completed"}
    response = client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 400
    assert "not supported" in response.json()["error"]


def test_checkout_immediate_payment_success(client):
    """Verify checkout submission with valid card completes order/payment immediately."""
    from apps.products.factories import ProductFactory

    user = UserFactory()
    client.force_login(user)

    product = ProductFactory(price=10.00, stock=5)
    # Add to cart
    client.post(reverse("cart:add_to_cart", kwargs={"product_id": product.id}), {"quantity": 1})

    method = PaymentMethodFactory(code="debit", name="Stripe Card")
    response = client.post(
        reverse("orders:checkout"),
        {
            "address_choice": "new",
            "full_name": "Jane Doe",
            "phone": "+380501234567",
            "city": "Lviv",
            "address": "Galitska Sq 5",
            "payment_method": method.id,
            "card_number": "4000 0000 0000 0002",
            "cvv": "123",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("accounts:order_history")

    order = Order.objects.get(user=user)
    assert order.status == Order.Status.PAID
    assert order.payment.status == Payment.Status.COMPLETED


def test_checkout_payment_form_invalid(client):
    """Verify checkout fails validation and re-renders if payment details are invalid."""
    from apps.products.factories import ProductFactory

    user = UserFactory()
    client.force_login(user)

    product = ProductFactory(price=10.00, stock=5)
    client.post(reverse("cart:add_to_cart", kwargs={"product_id": product.id}), {"quantity": 1})

    method = PaymentMethodFactory(code="debit", name="Stripe Card")
    response = client.post(
        reverse("orders:checkout"),
        {
            "address_choice": "new",
            "full_name": "Jane Doe",
            "phone": "+380501234567",
            "city": "Lviv",
            "address": "Galitska Sq 5",
            "payment_method": method.id,
            "card_number": "",  # invalid card number
            "cvv": "123",
        },
    )

    assert response.status_code == 200
    from django.contrib.messages import get_messages

    assert "Invalid payment details provided." in [
        str(m) for m in get_messages(response.wsgi_request)
    ]
