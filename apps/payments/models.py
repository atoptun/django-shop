from django.db import models
from safedelete.config import SOFT_DELETE_CASCADE
from safedelete.models import SafeDeleteModel

from apps.orders.models import Order


class PaymentMethod(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class Payment(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    payment_method = models.ForeignKey(
        PaymentMethod, on_delete=models.PROTECT, related_name="payments", null=True
    )
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        method_name = self.payment_method.name if self.payment_method else "Unknown"
        return f"Payment for Order #{self.order.pk} via {method_name} ({self.status})"
