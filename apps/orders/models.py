from django.conf import settings
from django.db import models
from django.urls import reverse
from safedelete.config import SOFT_DELETE_CASCADE
from safedelete.models import SafeDeleteModel

from apps.products.models import Product


class Order(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

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

    class Meta:
        ordering = ["-created_at"]

    @property
    def get_absolute_url(self):
        # TODO: Implement a proper URL for order detail view
        return reverse("orders:order_detail", kwargs={"pk": self.pk})

    def __str__(self):
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
    def subtotal(self) -> models.DecimalField:
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name if self.product else 'Unknown Product'}"


class Payment(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    class Method(models.TextChoices):
        CREDIT_CARD = "credit_card", "Credit Card"
        PAYPAL = "paypal", "PayPal"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    method = models.CharField(max_length=20, choices=Method.choices)
    transaction_id = models.CharField(max_length=100, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for Order #{self.order.pk} via {self.method}"


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of {self.user.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="unique_cart_product")
        ]

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Cart"

    @property
    def subtotal(self):
        return self.product.price * self.quantity
