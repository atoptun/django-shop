import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV", ".env"),
        extra="ignore",
    )
    app_name: str = "Django Shop"

    debug: bool = False

    log_level: str = "info"
    log_file: str = ""

    # Django settings
    DJANGO_SECRET_KEY: str = "django-insecure-dev-key-change-in-production"
    DJANGO_ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]

    DJANGO_SUPERUSER_USERNAME: str = "admin"
    DJANGO_SUPERUSER_EMAIL: str = "admin@django-shop.com"
    DJANGO_SUPERUSER_PASSWORD: str = ""

    # Database settings
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "django_shop"

    @property
    def postgres_url(self) -> str:
        return (
            f"postgres://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Email settings
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_USE_TLS: bool = True
    EMAIL_HOST_USER: str = ""
    EMAIL_HOST_PASSWORD: str = ""
    DEFAULT_FROM_EMAIL: str = "noreply@django-shop.com"


config = Settings()
