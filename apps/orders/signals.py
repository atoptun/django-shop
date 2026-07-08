from typing import Any

from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.http import HttpRequest

from apps.cart.services import CartService


@receiver(user_logged_in)
def merge_cart_on_login(
    sender: Any, request: HttpRequest, user: AbstractBaseUser, **kwargs: Any
) -> None:
    """Signal receiver to merge the session cart with the DB cart when a user logs in."""
    cart_service = CartService(request, user=user)
    cart_service.merge_session_cart()
