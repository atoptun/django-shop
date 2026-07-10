from typing import cast

from django.utils.decorators import method_decorator
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, generics, status, viewsets
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
    UserAddressSerializer,
    UserProfileSerializer,
    UserRegisterResponseSerializer,
    UserRegisterSerializer,
)


@extend_schema(
    tags=["User Authentication"],
    description="Obtain JWT tokens for user authentication.",
)
class UserLoginView(SimpleJWTTokenObtainPairView):
    pass


@extend_schema(
    tags=["User Authentication"],
    description="Refresh JWT access tokens using a refresh token.",
)
class UserTokenRefreshView(SimpleJWTTokenRefreshView):
    pass


@extend_schema(
    tags=["User Authentication"],
    description="Register a new user account.",
)
class UserRegisterAPIView(generics.CreateAPIView):
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


@extend_schema(
    tags=["User Profile"],
    description="Get or update the authenticated user's profile.",
)
class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        request = cast(AuthenticatedRequest, self.request)
        return request.user


@extend_schema(
    tags=["User Addresses"],
    description="Manage the authenticated user's addresses.",
)
@method_decorator(
    name="list",
    decorator=extend_schema(
        parameters=[
            OpenApiParameter(
                name="ordering",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Sorting options for the results.",
                enum=[
                    "recipient_name",
                    "-recipient_name",
                    "city",
                    "-city",
                    "created_at",
                    "-created_at",
                ],
            )
        ]
    ),
)
class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = UserAddressSerializer
    permission_classes = [IsOwner]

    search_fields = ["recipient_name", "phone", "city", "address_line"]

    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ["recipient_name", "city", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Address.objects.none()
        request = cast(AuthenticatedRequest, self.request)
        return Address.objects.filter(user=request.user)

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
