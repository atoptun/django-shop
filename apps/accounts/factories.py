import factory
from django.contrib.auth import get_user_model

from apps.accounts.models import Address, Profile

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user_{n}")  # type: ignore
    email = factory.Sequence(lambda n: f"user_{n}@example.com")  # type: ignore
    first_name = "John"
    last_name = "Doe"
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "password123")
        user = super()._create(model_class, *args, **kwargs)
        user.set_password(password)
        user.save()
        return user


class ProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Profile

    user = factory.SubFactory(UserFactory)  # type: ignore
    phone = "+380991234567"
    city = "Kyiv"
    address = "Test Street 123"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        user = kwargs.get("user")
        if user and hasattr(user, "profile"):
            profile = user.profile
            for key, value in kwargs.items():
                if key != "user":
                    setattr(profile, key, value)
            profile.save()
            return profile
        return super()._create(model_class, *args, **kwargs)


class AddressFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Address

    profile = factory.SubFactory(ProfileFactory)  # type: ignore
    recipient_name = "Jane Doe"
    phone = "+380501234567"
    city = "Kyiv"
    address_line = "Khreshchatyk St, 1, apt 10"
    is_default = False
