import pytest
from django.core.management import call_command


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Override the default django_db_setup fixture to seed the test database.
    """
    with django_db_blocker.unblock():
        call_command("seed_products")
