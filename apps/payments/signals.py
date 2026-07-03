from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.orders.models import Order
from apps.payments.models import Payment


@receiver(post_save, sender=Order)
def auto_confirm_cod_payment(sender, instance, **kwargs):
    """Automatically marks Cash On Delivery payments as COMPLETED when the Order is delivered."""
    if instance.status == Order.Status.DELIVERED:
        try:
            payment = instance.payment
            if payment.payment_method and payment.payment_method.code == "cod":
                if payment.status != Payment.Status.COMPLETED:
                    payment.status = Payment.Status.COMPLETED
                    payment.save()
        except Payment.DoesNotExist:
            pass
