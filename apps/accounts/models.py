from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from phonenumber_field.modelfields import PhoneNumberField
from safedelete.config import SOFT_DELETE_CASCADE
from safedelete.models import SafeDeleteModel

from apps.orders.models import Order
from apps.reviews.models import Review


class User(AbstractUser, SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE
    profile: "Profile"
    orders: models.QuerySet["Order"]
    reviews: models.QuerySet["Review"]

    class Meta:
        db_table = "auth_user"


class Profile(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, related_name="profile")
    phone = PhoneNumberField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)

    addresses: models.QuerySet["Address"]

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


# @receiver(post_save, sender=User)
# def save_user_profile(sender, instance, **kwargs):
#     if hasattr(instance, 'profile'):
#         instance.profile.save()


class Address(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="addresses")
    recipient_name = models.CharField(max_length=255)
    phone = PhoneNumberField()
    city = models.CharField(max_length=100)
    address_line = models.TextField()
    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Addresses"

    def __str__(self):
        return f"{self.recipient_name} - {self.city}, {self.address_line}"

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(profile=self.profile, is_default=True).exclude(
                pk=self.pk
            ).update(is_default=False)
        super().save(*args, **kwargs)
