from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from faker import Faker

from apps.accounts.models import Address, User


class Command(BaseCommand):
    help = "Seed the database with 20 fake addresses for a user profile."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--username",
            type=str,
            help=(
                "The username of the user to seed addresses for."
                " If not provided, seeds for the first user/profile found."
            ),
        )
        parser.add_argument(
            "--quantity",
            type=int,
            default=20,
            help=("The number of fake addresses to seed. Default is 20 addresses."),
        )

    def handle(self, *args, **options: dict[str, Any]) -> None:
        fake = Faker()
        username = options.get("username")
        quantity: int = options["quantity"]  # type: ignore[assignment]

        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"User with username '{username}' does not exist.")
                )
                return
        else:
            self.stdout.write(self.style.ERROR("User required."))
            return

        profile = user.profile
        self.stdout.write(
            self.style.NOTICE(
                f"Seeding {quantity} fake addresses for user '{user.username}'"
                f" (Profile ID: {profile.pk})..."
            )
        )

        created_count = 0
        for _ in range(quantity):
            # Generate a valid E.164 phone number
            phone_num = f"+38050{fake.random_number(digits=7, fix_len=True)}"

            # The first address will be default if no default address exists yet
            is_default = False
            if not user.addresses.filter(is_default=True).exists() and created_count == 0:
                is_default = True

            Address.objects.create(
                user=user,
                recipient_name=fake.name(),
                phone=phone_num,
                city=fake.city(),
                address_line=fake.street_address(),
                is_default=is_default,
            )
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {created_count} addresses."))
