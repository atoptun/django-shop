import factory

from apps.orders.factories import OrderFactory
from apps.payments.models import Payment, PaymentMethod


class PaymentMethodFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PaymentMethod
        django_get_or_create = ("code",)

    code = "debit"
    name = "Debit Card"
    is_active = True


class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payment

    order = factory.SubFactory(OrderFactory)  # type: ignore
    payment_method = factory.SubFactory(PaymentMethodFactory)  # type: ignore
    transaction_id = factory.Sequence(lambda n: f"txn_{n}")  # type: ignore
    status = Payment.Status.COMPLETED
