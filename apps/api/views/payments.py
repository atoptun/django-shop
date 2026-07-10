from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from apps.api.serializers.payments import PaymentMethodSerializer
from apps.payments.models import PaymentMethod


@extend_schema(
    tags=["Payments"],
    description="API view set for managing payment methods.",
)
class PaymentMethodViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentMethodSerializer

    permission_classes = [AllowAny]

    filter_backends = []

    pagination_class = None

    def get_queryset(self):
        """Evaluate queryset per-request to capture runtime changes cleanly."""
        return PaymentMethod.objects.filter(is_active=True)

    @extend_schema(
        summary="List available payment methods",
        description="Returns a list of active payment methods available for order checkout.",
        responses={200: PaymentMethodSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(exclude=True)
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
