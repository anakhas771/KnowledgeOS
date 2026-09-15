from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.services.authentication import AuthenticationService
from apps.organizations.models import Organization

User = get_user_model()


class AccountsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = "/api/v1/auth/register/"
        self.login_url = "/api/v1/auth/login/"
        self.me_url = "/api/v1/auth/me/"

        self.user = AuthenticationService.register_user(
            organization_name="Test Org",
            organization_slug="test-org",
            email="admin@example.com",
            username="adminuser",
            password="StrongPassword123!",
        )

        self.employee = User.objects.create_user(
            username="employee",
            email="employee@example.com",
            password="EmployeePassword123!",
            organization=self.user.organization,
        )
        # Defaults to EMPLOYEE role

    def test_invalid_login_rejected(self):
        """Verify that invalid credentials are rejected with a 401."""
        response = self.client.post(
            self.login_url,
            {"username": "adminuser", "password": "WrongPassword!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", response.data)

    def test_valid_login_returns_tokens(self):
        """Verify that valid credentials return JWT tokens."""
        response = self.client.post(
            self.login_url,
            {"username": "adminuser", "password": "StrongPassword123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        self.assertTrue("refresh" in response.cookies)
        self.assertEqual(response.cookies["refresh"]["httponly"], True)

    def test_me_view_authenticated_access(self):
        """Verify that an authenticated user can fetch their profile."""
        self.client.force_authenticate(user=self.employee)
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "employee")
        self.assertEqual(response.data["role"], User.Role.EMPLOYEE)
        self.assertEqual(response.data["organization"]["name"], "Test Org")

    def test_me_view_unauthenticated_rejected(self):
        """Verify that an unauthenticated user cannot access the MeView."""
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_mass_assignment_prevented_during_registration(self):
        """
        Verify that a client cannot mass-assign privileged fields like 'role'
        or 'is_superuser' during registration.
        """
        payload = {
            "organization_name": "Hacker Org",
            "organization_slug": "hacker-org",
            "email": "hacker@example.com",
            "username": "hacker",
            "password": "StrongPassword123!",
            "role": "admin",
            "is_superuser": True,
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Retrieve the created user
        user = User.objects.get(username="hacker")
        
        # The user should be an ADMIN because they created the organization
        self.assertEqual(user.role, User.Role.ADMIN)
        # But they should NOT be a Django superuser
        self.assertFalse(user.is_superuser)
