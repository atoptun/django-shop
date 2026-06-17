import os
from typing import cast

from django.contrib.auth import get_user_model
from django.contrib.auth.models import UserManager
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Create a superuser if it doesn't exist."

    def handle(self, *args, **options):
        # print("Creating superuser if it doesn't exist...")
        username = os.getenv("DJANGO_SUPERUSER_USERNAME")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

        if not username or not password:
            self.stdout.write(self.style.WARNING("Variables for superuser not found in env."))
            return

        if not User.objects.filter(username=username).exists():
            user_manager = cast(UserManager, User.objects)
            user_manager.create_superuser(username=username, email=email, password=password)
            self.style.SUCCESS(self.style.SUCCESS(f'Superuser "{username}" created successfully.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" already exists.'))
