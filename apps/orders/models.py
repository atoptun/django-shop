import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models
from django.urls import NoReverseMatch, reverse
from safedelete.config import SOFT_DELETE_CASCADE
from safedelete.models import SafeDeleteModel

from apps.products.models import Product


class Order(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="orders"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    if TYPE_CHECKING:
        from apps.payments.models import Payment

        items: models.Manager["OrderItem"]
        payment: "Payment"

    class Meta:
        ordering = ["-created_at"]

    def get_absolute_url(self) -> str:
        try:
            return reverse("orders:order_detail", kwargs={"pk": self.pk})
        except NoReverseMatch:
            return reverse("accounts:order_history")

    def __str__(self) -> str:
        return f"Order #{self.pk} by {self.user.username if self.user else 'Unknown'}"


class OrderItem(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, null=True, related_name="order_items"
    )
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(fields=["order", "product"], name="unique_order_product")
        ]

    @property
    def subtotal(self) -> Decimal:
        return self.price * self.quantity

    def __str__(self) -> str:
        return f"{self.quantity} x {self.product.name if self.product else 'Unknown Product'}"
