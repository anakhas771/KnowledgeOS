from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from apps.accounts.services.authentication import AuthenticationService
from apps.organizations.models import Organization
from apps.accounts.permissions import IsOrganizationAdmin

User = get_user_model()


class AuthenticationServiceTests(TestCase):
    def test_registration_creator_becomes_admin(self):
        """
        Verify that creating a new organization assigns the ADMIN role
        to the user who created it.
        """
        user = AuthenticationService.register_user(
            organization_name="Test Org",
            organization_slug="test-org",
            email="creator@test.com",
            username="creator",
            password="testpassword123",
        )

        # Assert organization was created
        self.assertIsNotNone(user.organization)
        self.assertEqual(user.organization.name, "Test Org")

        # Assert user role is ADMIN
        self.assertEqual(user.role, User.Role.ADMIN)

    def test_ordinary_user_defaults_to_employee(self):
        """
        Verify that creating a normal user (not via registration service)
        defaults to the EMPLOYEE role to avoid escalating privileges.
        """
        org = Organization.objects.create(name="Other Org", slug="other")
        user = User.objects.create_user(
            username="ordinary",
            email="ordinary@test.com",
            password="password",
            organization=org,
        )

        self.assertEqual(user.role, User.Role.EMPLOYEE)

    def test_admin_permissions_allow_creator(self):
        """
        Verify that the newly registered creator passes the IsOrganizationAdmin
        permission check.
        """
        user = AuthenticationService.register_user(
            organization_name="Admin Org",
            organization_slug="admin-org",
            email="admin@admin.com",
            username="adminuser",
            password="password",
        )

        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = user

        permission = IsOrganizationAdmin()
        has_permission = permission.has_permission(request, view=None)

        self.assertTrue(has_permission, "The registered creator should pass admin permission checks.")
