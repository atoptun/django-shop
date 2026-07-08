from rest_framework import serializers

from apps.products.models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "children"]

    def get_children(self, obj: Category):
        children = obj.children.all()
        return CategorySerializer(children, many=True, context=self.context).data


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, allow_null=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True, allow_null=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "price",
            "category_name",
            "category_slug",
            "image",
            "stock",
            "average_rating",
            "price_tag",
        ]
