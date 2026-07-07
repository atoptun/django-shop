from rest_framework.request import Request as DRFRequest

from apps.accounts.models import User


class AuthenticatedRequest(DRFRequest):
    user: User
