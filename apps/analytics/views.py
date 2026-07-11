from typing import Any, cast

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from graphene_django.views import GraphQLView
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class PrivateGraphQLView(GraphQLView):
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """
        Enforces staff-only access via JWT Bearer token or a session cookie.
        If the user is not authenticated or not a staff member, raises PermissionDenied.
        """
        user = None

        try:
            result = JWTAuthentication().authenticate(cast(Request, request))
            if result:
                user, _ = result
        except (InvalidToken, TokenError):
            pass

        if user is None and request.user.is_authenticated:
            user = request.user

        if user is None or not user.is_staff:  # type: ignore[union-attr]
            raise PermissionDenied("You do not have permission.")

        request.user = user
        return super().dispatch(request, *args, **kwargs)
