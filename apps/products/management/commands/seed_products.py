import json
import os
import random
from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.products.models import Category, Product


class Command(BaseCommand):
    help = "Seed database with products and categories loaded from local products_data.json file."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Force re-seeding of products.",
        )

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

        product_count = Product.objects.count()
        if product_count > 0 and not options["force"]:
            self.stdout.write(
                self.style.WARNING(
                    f"{product_count} products already exist. Use --force to re-seed."
                )
            )
            return

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

            if created:
                call_command(
                    "seed_reviews",
                    product.slug,
                    quantity=random.randint(1, 5),
                    status="approved",
                )

        self.stdout.write(self.style.SUCCESS("Product seeding completed successfully!"))
