from django.core.management.base import BaseCommand, CommandParser
from faker import Faker

from apps.accounts.models import Address, User


class Command(BaseCommand):
    help = "Seed the database with 20 fake addresses for a user profile."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--username",
            type=str,
            help=str(
                (
                    "The username of the user to seed addresses for.",
                    " If not provided, seeds for the first user/profile found.",
                )
            ),
        )

    def handle(self, *args, **options: dict[str, str]) -> None:
        fake = Faker()
        username = options.get("username")

        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"User with username '{username}' does not exist.")
                )
                return
        else:
            user = User.objects.first()
            if not user:
                self.stdout.write(
                    self.style.WARNING("No user found. Creating a dummy seed user 'seed_user'...")
                )
                user = User.objects.create_user(
                    username="seed_user",
                    email="seed_user@example.com",
                    password="password123",
                    first_name="Seed",
                    last_name="User",
                )

        profile = user.profile
        self.stdout.write(
            self.style.NOTICE(
                f"Seeding 20 fake addresses for user '{user.username}' (Profile ID: {profile.pk})..."
            )
        )

        created_count = 0
        for _ in range(20):
            # Generate a valid E.164 phone number
            phone_num = f"+38050{fake.random_number(digits=7, fix_len=True)}"

            # The first address will be default if no default address exists yet
            is_default = False
            if not profile.addresses.filter(is_default=True).exists() and created_count == 0:
                is_default = True

            Address.objects.create(
                profile=profile,
                recipient_name=fake.name(),
                phone=phone_num,
                city=fake.city(),
                address_line=fake.street_address(),
                is_default=is_default,
            )
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {created_count} addresses."))
