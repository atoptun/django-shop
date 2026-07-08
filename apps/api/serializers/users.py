from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import Address, Profile, User


class TokenPairSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()


class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for profile model.
    """

    class Meta:
        model = Profile
        fields = ("phone", "city", "address")


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user and profile.
    """

    profile = ProfileSerializer()

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "profile")
        read_only_fields = ("id", "email")

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if profile_data is not None:
            profile_instance, _ = Profile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(profile_instance, attr, value)
            profile_instance.save()

        return instance


class UserRegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """

    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ("email", "password")

    def validate(self, data: dict) -> dict:
        if User.objects.filter(email=data["email"]).exists():
            raise serializers.ValidationError(
                {"error": "Registration with this email is prohibited."}
            )
        if data["email"]:
            data["username"] = data["email"]
        return data

    def create(self, validated_data: dict) -> User:
        return User.objects.create_user(**validated_data)  # type: ignore


class AddressSerializer(serializers.ModelSerializer):
    """
    Serializer for address model.
    """

    class Meta:
        model = Address
        fields = ("id", "recipient_name", "phone", "city", "address_line", "is_default")
        read_only_fields = ("id",)
