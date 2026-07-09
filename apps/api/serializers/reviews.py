from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.reviews.models import Review

User = get_user_model()


class ReviewUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username"]


class ReviewSerializer(serializers.ModelSerializer):
    user = ReviewUserSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ["id", "rating", "comment", "created_at", "user"]


class ReviewCreateSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=1000)
