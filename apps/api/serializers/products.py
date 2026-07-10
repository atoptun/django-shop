from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.products.models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["slug", "name", "children"]

    @extend_schema_field(serializers.ListSerializer(child=serializers.DictField()))
    def get_children(self, obj: Category):
        children_map = self.context.get("children_map")

        if children_map is not None and obj.pk is not None:
            children = children_map.get(obj.pk, [])
        else:
            children = obj.children.all()

        return CategorySerializer(children, many=True, context=self.context).data


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, allow_null=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True, allow_null=True)

    class Meta:
        model = Product
        fields = [
            "slug",
            "name",
            "price",
            "category_name",
            "category_slug",
            "image",
            "stock",
            "average_rating",
            "price_tag",
            "technical_specifications",
        ]


class ProductShortSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, allow_null=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True, allow_null=True)

    class Meta:
        model = Product
        fields = [
            "slug",
            "name",
            "price",
            "category_name",
            "category_slug",
            "image",
            "average_rating",
            "price_tag",
        ]
