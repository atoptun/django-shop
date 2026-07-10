from drf_spectacular.utils import PolymorphicProxySerializer
from rest_framework import serializers

from apps.payments.models import Payment, PaymentMethod


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ["code", "name"]
        read_only_fields = ["code", "name"]


class PaymentSerializer(serializers.ModelSerializer):
    payment_method_code = serializers.ReadOnlyField(source="payment_method.code")

    class Meta:
        model = Payment
        fields = ["payment_method_code", "transaction_id", "status", "created_at", "updated_at"]
        read_only_fields = [
            "payment_method_code",
            "transaction_id",
            "status",
            "created_at",
            "updated_at",
        ]


class PaymentSubmitSerializer(serializers.Serializer):
    payment_method_code = serializers.CharField()
    payment_data = serializers.DictField(required=False, default=dict)


# Serializer schemas for Swagger documentation
# --- Sub-serializers for schema documentation ---
class CardDetailsSerializer(serializers.Serializer):
    card_number = serializers.CharField(help_text="Card number, e.g. 4000 0000 0000 0002")
    cvv = serializers.CharField(max_length=4)


class PayPalDetailsSerializer(serializers.Serializer):
    paypal_email = serializers.EmailField()


class EmptyDetailsSerializer(serializers.Serializer):
    pass


# Schema Serializer (used only by Swagger/Spectacular docs) ---
class PaymentSubmitSchemaSerializer(serializers.Serializer):
    payment_method_code = serializers.CharField()
    payment_data = PolymorphicProxySerializer(
        component_name="PaymentData",
        serializers={
            "debit": CardDetailsSerializer,
            "wallet": PayPalDetailsSerializer,
            "bank": EmptyDetailsSerializer,
            "cod": EmptyDetailsSerializer,
        },
        resource_type_field_name="payment_method_code",
    )
