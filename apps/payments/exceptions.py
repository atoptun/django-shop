class PaymentError(Exception):
    """Base class for all payment-related errors."""

    pass


class OrderAlreadyPaidError(PaymentError):
    """Raised if trying to pay for an order that is already in PAID status."""

    pass


class PaymentAlreadyCompletedError(PaymentError):
    """Raised if the associated Payment transaction is already COMPLETED."""

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
