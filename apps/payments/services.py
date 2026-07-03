from django.db import transaction

from apps.orders.models import Order
from apps.payments.models import Payment, PaymentMethod
from apps.payments.providers import PaymentProviderFactory


class PaymentService:
    @staticmethod
    def process_order_payment(order: Order, payment_method: PaymentMethod, data: dict) -> dict:
        """Processes payment via simulated provider and updates order status accordingly."""
        simulator = PaymentProviderFactory.get_simulator(payment_method.code)
        result = simulator.process_payment(order, data)

        with transaction.atomic():
            payment, _ = Payment.objects.get_or_create(order=order)
            payment.payment_method = payment_method
            payment.status = result["status"]
            if result["transaction_id"]:
                payment.transaction_id = result["transaction_id"]
            payment.save()

            # Update order status if payment is completed
            if payment.status == Payment.Status.COMPLETED:
                order.status = Order.Status.PAID
                order.save()

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
