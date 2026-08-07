from django.contrib.auth import get_user_model
from django.db import transaction

from apps.organizations.models import Organization

User = get_user_model()


class AuthenticationService:
    """Business logic for user registration and authentication."""

    @staticmethod
    @transaction.atomic
    def register_user(
        *,
        organization_name: str,
        organization_slug: str,
        email: str,
        username: str,
        password: str,
    ):
        """Create an organization and its initial user."""

        organization = Organization.objects.create(
            name=organization_name,
            slug=organization_slug,
        )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            organization=organization,
        )

        return user