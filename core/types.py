from django.http import HttpRequest

from apps.accounts.models import User


class AuthenticatedRequest(HttpRequest):
    user: User

