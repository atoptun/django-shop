import uuid

from apps.orders.models import Order
from apps.payments.exceptions import PaymentError
from apps.payments.models import Payment


class PaymentProviderNotFound(PaymentError, ValueError):
    """Exception raised when a requested payment provider is not found or supported."""

    pass


class BasePaymentSimulator:
    def process_payment(self, order: Order, data: dict) -> dict:
        raise NotImplementedError("Subclasses must implement process_payment")

    def process_webhook(self, payload: dict) -> dict:
        raise NotImplementedError("Subclasses must implement process_webhook")


class StripeSimulator(BasePaymentSimulator):
    def process_payment(self, order: Order, data: dict) -> dict:
        card_number = data.get("card_number", "").replace(" ", "")
        cvv = data.get("cvv", "")

        if card_number == "4000000000000005" or cvv == "000":
            return {
                "success": False,
                "error": "Card Insufficient Funds / Verification Failed (simulated)",
                "transaction_id": None,
                "status": Payment.Status.FAILED,
            }

        return {
            "success": True,
            "error": None,
            "transaction_id": f"ch_stripe_{uuid.uuid4().hex[:12]}",
            "status": Payment.Status.COMPLETED,
        }

    def process_webhook(self, payload: dict) -> dict:
        event_type = payload.get("event")
        transaction_id = payload.get("transaction_id")
        status = payload.get("status")

        if event_type == "checkout.session.completed" and status == "completed":
            return {
                "success": True,
                "transaction_id": transaction_id,
                "status": Payment.Status.COMPLETED,
            }
        return {
            "success": False,
            "error": f"Unhandled Stripe event: {event_type}",
            "transaction_id": transaction_id,
        }


class PayPalSimulator(BasePaymentSimulator):
    def process_payment(self, order: Order, data: dict) -> dict:
        email = data.get("email", "")
        if "decline" in email.lower():
            return {
                "success": False,
                "error": "PayPal Account Verification Failed / Rejected (simulated)",
                "transaction_id": None,
                "status": Payment.Status.FAILED,
            }

        return {
            "success": True,
            "error": None,
            "transaction_id": f"txn_paypal_{uuid.uuid4().hex[:12]}",
            "status": Payment.Status.COMPLETED,
        }

    def process_webhook(self, payload: dict) -> dict:
        event_type = payload.get("event")
        transaction_id = payload.get("transaction_id")
        status = payload.get("status")

        if event_type == "PAYMENT.CAPTURE.COMPLETED" and status == "completed":
            return {
                "success": True,
                "transaction_id": transaction_id,
                "status": Payment.Status.COMPLETED,
            }
        return {
            "success": False,
            "error": f"Unhandled PayPal event: {event_type}",
            "transaction_id": transaction_id,
        }


class BankTransferSimulator(BasePaymentSimulator):
    def process_payment(self, order: Order, data: dict) -> dict:
        return {
            "success": True,
            "error": None,
            "transaction_id": f"ib_bank_{uuid.uuid4().hex[:12]}",
            "status": Payment.Status.PROCESSING,
        }

    def process_webhook(self, payload: dict) -> dict:
        transaction_id = payload.get("transaction_id")
        status = payload.get("status")

        if status == "completed":
            return {
                "success": True,
                "transaction_id": transaction_id,
                "status": Payment.Status.COMPLETED,
            }
        return {
            "success": False,
            "error": f"Unhandled Bank Transfer status: {status}",
            "transaction_id": transaction_id,
        }


class CashOnDeliverySimulator(BasePaymentSimulator):
    def process_payment(self, order: Order, data: dict) -> dict:
        return {
            "success": True,
            "error": None,
            "transaction_id": f"cod_{uuid.uuid4().hex[:12]}",
            "status": Payment.Status.PENDING,
        }

    def process_webhook(self, payload: dict) -> dict:
        transaction_id = payload.get("transaction_id")
        return {
            "success": False,
            "error": "Cash On Delivery webhooks are not supported. Confirm via admin.",
            "transaction_id": transaction_id,
        }


class PaymentProviderFactory:
    @staticmethod
    def get_simulator(code: str) -> BasePaymentSimulator:
        code_lower = code.lower()
        if "debit" in code_lower or "stripe" in code_lower:
            return StripeSimulator()
        elif "paypal" in code_lower or "wallet" in code_lower:
            return PayPalSimulator()
        elif "bank" in code_lower:
            return BankTransferSimulator()
        elif "cod" in code_lower:
            return CashOnDeliverySimulator()

        raise PaymentProviderNotFound(f"Payment provider with code '{code}' is not supported.")
