from django.db import transaction

from apps.orders.models import Order
from apps.payments.exceptions import (
    InvalidPaymentMethodError,
    OrderAlreadyPaidError,
    PaymentAlreadyCompletedError,
    PaymentDeclinedError,
    PaymentProcessingInProgressError,
)
from apps.payments.models import Payment, PaymentMethod
from apps.payments.providers import PaymentProviderFactory


class PaymentService:
    @staticmethod
    def process_order_payment(order: Order, payment_method_code: str, data: dict) -> dict:
        """Verifies order/payment states, checks payment method,
        processes payment, and updates DB.
        """
        # Step 1-6: State checking and verification under lock
        with transaction.atomic():
            # Lock the order row to prevent concurrent payment requests
            order = Order.objects.select_for_update().get(pk=order.pk)

            if order.status == Order.Status.PAID:
                raise OrderAlreadyPaidError("This order has already been paid.")

            # Retrieve or Create Payment under lock
            payment, _ = Payment.objects.select_for_update().get_or_create(order=order)

            if payment.status == Payment.Status.COMPLETED:
                raise PaymentAlreadyCompletedError(
                    "Payment for this order has already been completed."
                )

            if payment.status == Payment.Status.PROCESSING:
                raise PaymentProcessingInProgressError("Payment is already being processed.")

            try:
                payment_method = PaymentMethod.objects.get(code=payment_method_code, is_active=True)
            except PaymentMethod.DoesNotExist as e:
                raise InvalidPaymentMethodError("Payment method is invalid or inactive.") from e

            # Set payment to PROCESSING state to prevent concurrent requests from slipping through
            # while the payment simulator/gateway is executing.
            payment.status = Payment.Status.PROCESSING
            payment.payment_method = payment_method
            payment.save()

        # Step 7: Call provider (outside primary lock)
        simulator = PaymentProviderFactory.get_simulator(payment_method.code)
        result = simulator.process_payment(order, data)

        # Step 8: Update status and payment method atomically
        with transaction.atomic():
            # Refresh and lock payment row
            payment = Payment.objects.select_for_update().get(pk=payment.pk)

            # Double check status to avoid race condition
            if payment.status == Payment.Status.COMPLETED:
                raise PaymentAlreadyCompletedError(
                    "Payment for this order has already been completed."
                )

            payment.status = result["status"]
            if result["transaction_id"] is not None:
                payment.transaction_id = result["transaction_id"]
            payment.save()

            if payment.status == Payment.Status.COMPLETED:
                order = Order.objects.select_for_update().get(pk=order.pk)
                order.status = Order.Status.PAID
                order.save()

        # Step 9: If payment failed, raise PaymentDeclinedError
        # NOTE: If PaymentDeclinedError is raised, the payment transaction is persisted as FAILED,
        # but the order remains PENDING so that the customer can retry checkout.
        if payment.status == Payment.Status.FAILED:
            error_msg = result.get("error", "Transaction was declined.")
            raise PaymentDeclinedError(error_msg)

        return result

    @staticmethod
    def process_webhook_payment(provider_name: str, payload: dict) -> dict:
        """Finds provider simulator, delegates webhook parsing, and saves payment state."""
        simulator = PaymentProviderFactory.get_simulator(provider_name)
        result = simulator.process_webhook(payload)

        if result["success"]:
            with transaction.atomic():
                payment = Payment.objects.select_for_update().get(
                    transaction_id=result["transaction_id"]
                )
                payment.status = result["status"]
                payment.save()

                if payment.status == Payment.Status.COMPLETED:
                    order = payment.order
                    order.status = Order.Status.PAID
                    order.save()

        return result
