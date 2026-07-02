import random
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.products.models import Product
from apps.products.services import ProductService
from apps.reviews.models import Review

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds random reviews using Faker for a specified product."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "product_identifier",
            type=str,
            help="The slug or ID of the product to seed reviews for.",
        )
        parser.add_argument(
            "--quantity",
            "-q",
            type=int,
            default=5,
            help="Number of reviews to generate (default is 5).",
        )
        parser.add_argument(
            "--status",
            "-s",
            type=str,
            choices=[status.value for status in Review.Status],
            default=Review.Status.APPROVED.value,
            help="Moderation status of the generated reviews.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from faker import Faker

        fake = Faker()
        product_ident = options["product_identifier"]
        quantity = options["quantity"]
        status = options["status"]

        if quantity <= 0:
            raise CommandError("Quantity must be greater than zero.")

        # 1. Resolve product by ID or Slug
        try:
            if product_ident.isdigit():
                product = Product.objects.get(id=int(product_ident))
            else:
                product = Product.objects.get(slug=product_ident)
        except Product.DoesNotExist as err:
            raise CommandError(f"Product '{product_ident}' does not exist.") from err

        # 2. Get or create users to author reviews
        users = list(User.objects.all())
        if not users:
            self.stdout.write("No users found. Creating a fake user...")
            username = fake.user_name()
            email = fake.email()
            user = User.objects.create_user(  # type: ignore
                username=username, email=email, password="password123"
            )
            users.append(user)

        self.stdout.write(f"Seeding {quantity} reviews for '{product.name}'...")

        reviews_created = 0
        for _ in range(quantity):
            user = random.choice(users)

            # Avoid duplicate reviews by the same user on the same product
            attempts = 0
            while Review.objects.filter(product=product, user=user).exists() and attempts < 10:
                user = random.choice(users)
                attempts += 1

            if attempts >= 10:
                # Create a new fake user to avoid duplicate review collision
                username = fake.user_name()
                email = fake.email()
                user = User.objects.create_user(  # type: ignore
                    username=username, email=email, password="password123"
                )
                users.append(user)

            Review.objects.create(
                product=product,
                user=user,
                rating=random.randint(1, 5),
                comment=fake.paragraph(nb_sentences=random.randint(1, 4)),
                status=status,
            )
            reviews_created += 1

        # 3. Recalculate average rating of the product
        product_service = ProductService(request=None)  # type: ignore
        product_service.update_product_rating(product)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded {reviews_created} reviews. Product rating updated."
            )
        )
