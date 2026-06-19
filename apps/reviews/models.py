from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from safedelete.config import SOFT_DELETE_CASCADE
from safedelete.models import SafeDeleteModel

from apps.products.models import Product


class Review(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[
        MinValueValidator(1),
        MaxValueValidator(5)
    ])
    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Review by {self.user.username if self.user else 'Unknown'} for {self.product.name}"
