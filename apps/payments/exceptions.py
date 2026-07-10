class PaymentError(Exception):
    """Base class for all payment-related errors."""

    pass


class OrderAlreadyPaidError(PaymentError):
    """Raised if trying to pay for an order that is already in PAID status (order-level check)."""

    pass


class PaymentAlreadyCompletedError(PaymentError):
    """Raised if the order is not yet PAID but the associated Payment record

    is already COMPLETED (payment-level check).
    """

    pass


class PaymentProcessingInProgressError(PaymentError):
    """Raised if the associated Payment transaction is already in PROCESSING status."""

    pass


class InvalidPaymentMethodError(PaymentError):
    """Raised if the requested payment method code doesn't exist or is inactive."""

    pass


class PaymentDeclinedError(PaymentError):
    """Raised when the provider/gateway declines the transaction."""

    pass
