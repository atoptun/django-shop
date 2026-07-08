from typing import cast

from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import (
    TokenObtainPairView as SimpleJWTTokenObtainPairView,
)
from rest_framework_simplejwt.views import (
    TokenRefreshView as SimpleJWTTokenRefreshView,
)

from apps.accounts.models import Address

from ..permissions import IsOwner
from ..requests import AuthenticatedRequest
from ..serializers.users import (
    AddressSerializer,
    UserProfileSerializer,
    UserRegisterResponseSerializer,
    UserRegisterSerializer,
)


@extend_schema(tags=["User Authentication"])
class UserLoginView(SimpleJWTTokenObtainPairView):
    """
    Takes a set of user credentials and returns an access and refresh JWT.
    """

    pass


@extend_schema(tags=["User Authentication"])
class UserTokenRefreshView(SimpleJWTTokenRefreshView):
    """
    Takes a refresh type JSON web token and returns an access type JSON web token.
    """

    pass


@extend_schema(tags=["User Authentication"])
class UserRegisterAPIView(generics.CreateAPIView):
    """
    API view for user registration.
    """

    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]

    @extend_schema(responses={status.HTTP_201_CREATED: UserRegisterResponseSerializer})
    def post(self, request: Request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserProfileSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["User Profile"])
class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    """Get/update the authenticated user's profile."""

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        request = cast(AuthenticatedRequest, self.request)
        return request.user


@extend_schema(tags=["User Addresses"])
class AddressViewSet(viewsets.ModelViewSet):
    """ViewSet for managing addresses."""

    serializer_class = AddressSerializer
    permission_classes = [IsOwner]

    def get_queryset(self):
        request = cast(AuthenticatedRequest, self.request)
        return Address.objects.filter(user=request.user).order_by("-created_at")

    def create(self, request: AuthenticatedRequest, *args, **kwargs):
        is_many = isinstance(request.data, list)

        serializer = self.get_serializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        headers = {}
        if not is_many:
            headers = self.get_success_headers(serializer.data)

        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        request = cast(AuthenticatedRequest, self.request)
        serializer.save(user=request.user)
