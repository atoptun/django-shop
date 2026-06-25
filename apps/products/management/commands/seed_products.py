import json
import os

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.products.models import Category, Product


class Command(BaseCommand):
    help = "Seed database with products and categories loaded from local products_data.json file."

    def handle(self, *args, **options):
        self.stdout.write("Starting product seeding from JSON...")

        # Resolve path to products_data.json relative to this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, "products_data.json")

        if not os.path.exists(json_path):
            self.stdout.write(self.style.ERROR(f"File not found: {json_path}"))
            return

        with open(json_path, encoding="utf-8") as f:
            products_data = json.load(f)

        for p_data in products_data:
            name = p_data["name"]
            category_name = p_data["category"]

            category, _ = Category.objects.get_or_create(
                name=category_name, defaults={"slug": slugify(category_name)}
            )

            product, created = Product.objects.update_or_create(
                slug=p_data["slug"],
                defaults={
                    "name": name,
                    "description": p_data["description"],
                    "price": p_data["price"],
                    "price_tag": p_data["price_tag"],
                    "category": category,
                    "image": p_data["image"],
                    "stock": 50,
                    "technical_specifications": p_data["technical_specifications"],
                },
            )

            action = "Created" if created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(f"{action} product '{name}' (Category: {category_name})")
            )

        self.stdout.write(self.style.SUCCESS("Product seeding completed successfully!"))
