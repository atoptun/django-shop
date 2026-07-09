from django.contrib.auth.models import AbstractUser
from rest_framework.test import APIClient


class AuthClient(APIClient):
    user: AbstractUser
